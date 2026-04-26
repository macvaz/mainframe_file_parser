# mainframe-validator

Rust + Python project for parsing fixed-size mainframe files and writing Parquet shards.

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

## Run the example script

From project root (Rust wheel installed, input data at `data/huge_fixed_size_file.dat` as in `run.py`):

```bash
uv run run.py
```

The script prints how long `main()` took. **Timing:** if `data/huge_fixed_size_file.parquet` does not exist, `main()` finishes in **less than 3 seconds** (Parquet is generated first). If that Parquet file already exists, `main()` finishes in **single-digit milliseconds**.

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
