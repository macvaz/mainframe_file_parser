# file-validator

Pipeline to:

1. Generate a large fixed-size ASCII file
2. Parse fixed records using a COBOL copybook in Rust (high performance)
3. Convert to Parquet
4. Read Parquet in columnar mode with Polars

## Project structure

- `bin/generate_huge_ascii_file.py`: Generates test fixed-width ASCII data (>= 2 GiB by default)
- `schema/sample.cpy`: Example COBOL copybook
- `rust/`: Rust CLI that converts fixed ASCII records into Parquet
- `src/file_validator/read_parquet.py`: Polars lazy reader example
- `test/`: Pytest tests (small integration by default; huge file test is opt-in via ``--run-huge``)

## Record format

Example copybook:

```cobol
01 RECORD-LAYOUT.
   05 FULL_NAME           PIC A(50).
   05 YEAR                PIC 9(4).
   05 AMOUNT              PIC 9(9)V99.
```

This means:

- `FULL_NAME`: 50 chars (ASCII, padded)
- `YEAR`: 4 digits
- `AMOUNT`: 11 digits with implied decimal (`9(9)V99`)

Generated records are line-terminated (`\n`), so:

- payload width = `50 + 4 + 11 = 65` bytes
- record width with newline = `66` bytes

## Prerequisites

- Python 3.12+
- Rust toolchain (`cargo`, `rustc`)
- Recommended: virtual environment for Python deps

Install Cargo/Rust:

### Option A (recommended): rustup

```bash
curl https://sh.rustup.rs -sSf | sh
source "$HOME/.cargo/env"
```

### Option B (Ubuntu apt)

```bash
sudo apt update
sudo apt install -y cargo
```

Verify installation:

```bash
cargo --version
rustc --version
```

Install Python dependencies:

```bash
pip install -e .
```

## Build Rust Extension with maturin

Build the Rust extension wheel and install it into `.venv`:

```bash
source "$HOME/.cargo/env"
source .venv/bin/activate
maturin build --manifest-path rust/Cargo.toml -o rust/target/wheels
uv pip install --python .venv/bin/python --reinstall --no-deps \
  rust/target/wheels/fixed2parquet-0.1.0-cp312-cp312-manylinux_2_34_x86_64.whl
```

Wheel filename may differ slightly (platform tag); use `rust/target/wheels/fixed2parquet-*.whl` if needed.

Verify the Rust module import:

```bash
.venv/bin/python -c "from fixed2parquet import parse_copy_to_parquet; print(parse_copy_to_parquet)"
```

Run tests with **uv** (``pythonpath`` is set in ``pyproject.toml`` so ``src`` is on the path; dev group provides pytest):

```bash
uv sync --group dev
uv run pytest -q test/ -rs
```

Run only the small integration test:

```bash
uv run pytest -q test/test_integration_parse_copy.py -rs
```

Optional: full **multi-GB** fixture (`data/huge_fixed_size_file.dat`) is in `test/test_integration_huge_parse_copy.py` and is **not** collected unless you pass ``--run-huge`` (long runtime, large disk):

```bash
uv run pytest -q test/ --run-huge -rs
```

Notes:

- This project currently uses `setuptools` as the root build backend, so `uv run maturin develop` can conflict with dependency-group syncing in some environments.
- The commands above avoid that issue and are the tested working flow.

### Rust converter and CPU usage

Conversion uses **Rayon** to parse record batches in parallel on all available logical CPUs, while a **dedicated writer thread** applies ZSTD and writes Parquet in strict row order (so work overlaps instead of parsing and compression both piling onto one core).

On Linux you can sanity-check multi-threaded CPU time (includes all threads) vs wall time after `uv sync` and installing the `fixed2parquet` wheel; for a large run you should see **(user+sys CPU seconds) / wall seconds** clearly above `1.0` when more than one core is contributing (often roughly `1.2`–`3+` depending on disk and batch size).

## 1) Generate a huge fixed-size ASCII file

Default output size is at least 2 GiB.

```bash
python3 bin/generate_huge_ascii_file.py data/huge_fixed_size_file.dat
```

Optional:

```bash
python3 bin/generate_huge_ascii_file.py data/huge_fixed_size_file.dat --target-bytes 3221225472 --seed 123
```

## 2) Convert fixed ASCII to Parquet with Rust

Build and run (release mode recommended):

```bash
cd rust
cargo run --release -- \
  --input ../data/huge_fixed_size_file.dat \
  --copybook ../schema/sample.cpy \
  --output ../data/huge_fixed_size_file.parquet \
  --line-terminated true \
  --batch-records 500000 \
  --compression zstd
```

Notes:

- `--line-terminated true` expects one trailing `\n` per record.
- `--batch-records` controls memory/performance tradeoff.
- `--compression` supports `zstd` (default), `snappy`, `uncompressed`.
- `AMOUNT` is written as integer with implied decimals (for `9(9)V99`).

Performance note from local profiling on the 2.1GB fixture:

- `zstd`: ~24.8s, output ~0.646GB
- `snappy`: ~13.3s, output ~0.948GB
- `uncompressed`: ~7.3s, output ~1.021GB

## 3) Read Parquet with Polars (columnar)

Run from project root:

```bash
python3 -m file_validator.read_parquet data/huge_fixed_size_file.parquet --columns FULL_NAME YEAR AMOUNT --year-min 2000 --limit 10
```

This uses `scan_parquet()` (lazy API), enabling projection and predicate pushdown.

## Troubleshooting

- If `cargo` is missing, install Rust:
  - [https://rustup.rs/](https://rustup.rs/)
- If `ModuleNotFoundError: polars` appears:
  - `pip install -e .`

