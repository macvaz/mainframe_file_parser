# mainframe-validator

Rust + Python project for parsing fixed-size mainframe files and writing Parquet files with the resulting validations

## Rust Toolchain Setup

### 1) Install Rust (recommended: rustup)

```bash
curl https://sh.rustup.rs -sSf | sh -y
source "$HOME/.cargo/env"
```

### 2) Verify toolchain

```bash
rustc --version
cargo --version
```

### 3) Create/sync Python environment

```bash
uv sync --group dev
```

This installs development tools including `maturin`.

## Build the Rust Python Extension

From project root:

```bash
source "$HOME/.cargo/env"
source .venv/bin/activate
maturin build --release --manifest-path rust/Cargo.toml -o rust/target/wheels
uv pip install --python .venv/bin/python --reinstall --no-deps \
  rust/target/wheels/mainframe_tools-*.whl
```

For simplicity, there is a shell script in bin for automating building the rust extension:

```bash
bin/build_rust_extension.sh
```


## Verify Import

```bash
uv run python -c "import mainframe_tools; print(hasattr(mainframe_tools, 'parse_and_write_parquet'))"
```

Expected output: `True`

## Generate the huge fixed-width input file

The script `bin/generate_huge_ascii_file.py` writes a line-oriented fixed-width ASCII file (one record per line, payload + newline) from a **COBOL copybook**. Field positions and types are read with `file_validator.utils.cobol.get_schema_from_copybook`; **random values are chosen only from column types** (`string`, `integer`, `decimal`), not from field names. The copybook must only contain PICs that map to those three kinds (for example `X(n)`, `9(n)`, and implied-decimal `9…V99` numerics).

**Requirements:** project root, `src` on `PYTHONPATH` (or use the examples below), and enough free disk space (default output is at least **2 GiB**).

| Argument / option | Description |
| --- | --- |
| `copybook` | Path to the `.cpy` file (elementary `PIC` clauses). |
| `output` | Path of the generated `.dat` file (e.g. `data/huge_fixed_size_file.dat`). |
| `--target-bytes` | Minimum total file size in bytes (default: `2147483648`, i.e. 2 GiB; values below that are rejected). |
| `--seed` | RNG seed for reproducible records (default: `42`). |

**Example** using the repository fixture copybook (65-byte payload + newline per record):

```bash
uv run python bin/generate_huge_ascii_file.py \
  test/fixtures/sample_file_record.cpy \
  data/huge_fixed_size_file.dat
```

**Example** with your own copybook and explicit size/seed:

```bash
uv run python bin/generate_huge_ascii_file.py \
  path/to/YOUR.cpy \
  data/my_huge.dat \
  --target-bytes $((3 * 1024 ** 3)) \
  --seed 12345
```

Polars tends to saturate all available cpus so it can produce thermal throttling (specially in laptops) after several runs:

```bash
grep . /sys/devices/system/cpu/cpu*/thermal_throttle/*_count
```

To control it effectivaly, set the number of threads that polars will use with this environment variable:

```bash
export POLARS_MAX_THREADS=$(($(nproc) - 2))
```

After generation, point `run.py` at the same path as `INPUT_PATH` (or overwrite `data/huge_fixed_size_file.dat` so the default matches).

## Run the example script

From project root (Rust wheel installed, input data at `data/huge_fixed_size_file.dat` as in `run.py`):

```bash
uv run run.py
```

### Input file size (from notebook)

The huge sample matches **32,540,000** records: `notebooks/exploration.ipynb` cell 1 runs `pl.scan_parquet("data/huge_fixed_size_file.parquet/*").count().collect()`, which reports 32,540,000 rows for each of `FULL_NAME`, `YEAR`, and `AMOUNT` (same row count as the source fixed-width file once converted).

## Benchmarking the execution

`run.py` times two stages and prints seconds for each, plus total wall time:

1. **Stage 1** — `main()` converts the fixed-width file to **`INTERMEDIATE_OUTPUT_PATH`** (or skips writing if that path already exists and only sets up a scan).
2. **Stage 2** — `validation_etl` runs on the LazyFrame, the first 10 rows are collected for printing, then results are written to **`OUTPUT_PATH`**.

### Rust extension vs Polars (`file_parser`) — fixed-width → Parquet only

Stage 1 uses either the **Rust** extension (rayon-parallel) or the **Polars** path (lazy `scan_csv` + native `str.slice` / `cast`, sink to `data.parquet`). On the same input and machine, **both backends take about the same wall time** for conversion here—confirm with your own **`run.py`** timings.

| Backend | Time (same workload, same machine) | CPU during conversion |
| --- | ---: | --- |
| **Rust** (`file_validator.parsers.rust`) | **~6 s** (typical) | High utilization across cores |
| **Polars** (`file_validator.parsers.polars`) | **~6 s** (typical) | Comparable for this pipeline |

Figures are indicative (same fixed-width input and schema as `run.py`); absolute seconds vary by hardware, disk, and file size.

### Stage 1 / Stage 2 totals (`run.py`)

| Scenario | Stage 1: convert → `INTERMEDIATE_OUTPUT_PATH` | Stage 2: validations + write `OUTPUT_PATH` | Typical total |
| --- | --- | --- | --- |
| Intermediate Parquet **absent** (first conversion) | Parser (Rust or Polars) reads the `.dat` and writes intermediate Parquet; usually the larger part of the run. | Polars validation columns and writing the validation results to disk. | Often **~6.5 s** on a typical dev machine (varies by disk and data). |
| Intermediate Parquet **present** (reuse) | Near **0 s** — no rewrite; only opens a lazy scan of the existing file. | Same Stage 2 pipeline; usually dominates wall time on repeat runs. | Often **~3 s** (same caveat). |

Use the printed **Stage 1 / Stage 2 / Total** line for authoritative numbers on your machine.

### Example column validations

`run.py` applies `validation_etl` to the LazyFrame from `main()` and adds three boolean flags (one per source column):

| Source column | Flag | Rule |
| --- | --- | --- |
| `FULL_NAME` | `VALID_NAME` | String byte length is exactly 8 (`str.len_bytes() == 8`). |
| `YEAR` | `VALID_YEAR` | Integer year is between **1900** and **2000** (inclusive). |
| `AMOUNT` | `VALID_AMOUNT` | Decimal amount is between **0** and **672581176.44** (inclusive). |

The script then prints the first 10 rows with these flags materialized.

### `parse_and_write_parquet` column types

The schema dict maps each output column to `(byte_offset, length, type)`:

- `string` (default if you pass only `(offset, len)`)
- `integer` → Parquet `int64`
- `float` → `float64`
- `decimal(precision,scale)` → Parquet `decimal128`; value is trimmed ASCII digits interpreted with an implied decimal point before the last `scale` digits (COBOL `V` style). Example: PIC `9(9)V99` on 11 bytes → `decimal(11,2)`.

## Run Tests

Run default tests (huge test excluded by default):

```bash
uv run pytest -q test/ -rs
```

Run only the huge-file integration test:

```bash
uv run pytest -q test/test_integration_huge_mainframe_tools.py --run-huge -rs
```

Run all tests including huge:

```bash
uv run pytest -q test/ --run-huge -rs
```
