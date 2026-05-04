# mainframe-validator

High-performing Python-based project for parsing fixed-width mainframe files. This is a general pattern in reg tech projects (Regulatory Technologies). 

The data pipeline is the following:
  * Convert fixed-length file into a tabular analytical file (Parquet) and store it into disk
  * Applying a set of validation rules to the input file (each validation is an additional column of the dataframe computed in parallel with a boolean value)

It uses open-source high-performing analytical Python libraries (written in Rust) like polars, enabled with state-of-the-art technologies for fast analytics like
  - Apache Arrow
  - SIMD vectorized cpu instructions

For implementing the CI pipelines, mainstream open-source development tools are used from the astral.sh offering:
  - uv (project management + dependency management)
  - ruff (linter and formater)
  - ty (fast type checker)

## Generate the huge fixed-width input file

The script `bin/generate_huge_ascii_file.py` writes a line-oriented fixed-width ASCII file from an input **COBOL copybook**. **Random values are chosen only from column types** (`string`, `integer`, `decimal`), not from field names. 
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
The copybook used for generating the sample data is the following:

```bash
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
```


## Run the example script

From project root (Rust wheel installed, input data at `data/huge_fixed_size_file.dat` as in `run.py`):

```bash
uv run run.py
```

### Input file size (from notebook)

The huge sample matches **32,540,000** records: `notebooks/exploration.ipynb` cell 1 runs `pl.scan_parquet("data/huge_fixed_size_file.parquet/*").count().collect()`, which reports 32,540,000 rows for each of `FULL_NAME`, `YEAR`, and `AMOUNT` (same row count as the source fixed-width file once converted).

## Benchmarking the execution

`run.py` times two stages and prints seconds for each, plus total wall time:

1. **Stage 1** — `main()` converts the fixed-width file to **`INTERMEDIATE_OUTPUT_PATH`** in Apache Parquet.
2. **Stage 2** — `validation_etl` computes all file validations according to a given set of validations rules and store the results again in disk.

### Rust extension vs Polars (`file_parser`)

Two different parsers have been implemented:
  * In native Rust, a platform-dependent high-performing programing language
  * In pure python using polars 

According to experimental executions and benchmarkings, the execution wall time is the same between both implementations. Without any doubt, the python-based implementation is way simpler and more mantainable. No need to code in pure rust to get high-performing execution time.

| Backend | Time (same workload, same machine) | CPU during conversion |
| --- | ---: | --- |
| **Pure rust** (`file_validator.parsers.rust`) | **~6 s** (typical) | High utilization across cores |
| **Python using Polars** (`file_validator.parsers.polars`) | **~6 s** (typical) | Comparable for this pipeline |

Figures are indicative (same fixed-width input and schema as `run.py`); absolute seconds vary by hardware, disk, and file size.

### Stage 1 / Stage 2 totals (`run.py`)

| Scenario | Stage 1: convert → `INTERMEDIATE_OUTPUT_PATH` | Stage 2: validations + write `OUTPUT_PATH` | Typical total |
| --- | --- | --- | --- |
| Intermediate Parquet **absent** (first conversion) | Parser (Rust or Polars) reads the `.dat` and writes intermediate Parquet; usually the larger part of the run. | Polars validation columns and writing the validation results to disk. | Often **~6.5 s** on a typical dev machine (varies by disk and data). |
| Intermediate Parquet **present** (reuse) | Near **0 s** — no rewrite; only opens a lazy scan of the existing file. | Same Stage 2 pipeline; usually dominates wall time on repeat runs. | Often **~6 s** . |

Use the printed **Stage 1 / Stage 2 / Total** line for authoritative numbers on your machine.

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
