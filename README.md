# mainframe-validator

High-performing Python-based tool for parsing fixed-width mainframe files. This is a common pattern in Regtech projects (Regulatory Technologies) applied in the central banking sector.

## 1. Goal

According to many [technical assessments](https://niklas-heer.github.io/speed-comparison/), Rust is well-known as one of the fastest programming languages in execution time. Python is also known as one of the slowest.

The main goal of this repo is to benchmark two different implementations:
* a [Python](packages/file_validator/src/file_validator/parsers/polars/parser.py) parser (based on **polars** analytical library)
* a [Rust](packages/file_validator/rust/src/lib.rs) parser developed from the scratch

## 2. File parsing logic

The data pipeline is the same for both implementations:
  * Convert fixed-length file into a tabular analytical file (Parquet) and store it on disk
  * Apply a set of validation rules to the parquet file, generating a new column for each validation (for storing the validation results)

Both versions rely on open-source high-performing analytical libraries, enabling state-of-the-art data processing techniques like:
  * Apache Arrow
  * SIMD vectorized CPU instructions

## 3. Project structure and setup

The project is structured following a monorepo setup. Several python packages can be found in the [packages](packages/) folder.

```
mainframe_validator/
├── bin/
│   ├── build_rust_extension.sh      # build/install Rust parser wheel
│   └── generate_huge_ascii_file.py  # generate fixed-width sample data
├── data/                            # sample files (gitignored)
├── docs/
│   └── cpu_utilization.png
├── notebooks/
│   └── exploration.ipynb
├── packages/
│   ├── file_validator/              # fixed-width → Parquet pipeline
│   │   ├── rust/                    # Rust extension code
│   │   │   └── src/lib.rs
│   │   ├── src/file_validator/
│   │   │   ├── main.py
│   │   │   ├── parsers/
│   │   │   │   ├── polars/          # Polars-based parser
│   │   │   │   │   ├── parser.py
│   │   │   │   │   └── utils.py
│   │   │   │   └── rust/            # Python bindings to Rust extension
│   │   │   ├── types/
│   │   │   └── utils/               # COBOL copybook → schema, I/O helpers
│   │   │       ├── cobol.py
│   │   │       └── file_utils.py
│   │   ├── tests/
│   │   └── typings/mainframe_tools/
│   └── formula_engine/              # validation expression engine (Lark + Polars)
│       ├── src/formula_engine/
│       │   ├── engine.py
│       │   ├── grammar/
│       │   └── graph/
│       └── tests/
├── conftest.py
├── pyproject.toml                   # workspace root (uv)
├── run.py                           # benchmark entrypoint
└── uv.lock
```

The project is managed using **uv**. To create the python virtual environment and download the dependencies of all the packages, run:

```console
uv sync --all-packages
```

Additionally, using **Jupyter notebooks** is highly recommended to quick experimentation with the code. In the [notebooks](notebooks/) folder some working examples are available.

## 4. CI pipelines

To implement the CI pipelines, mainstream open-source development tools are used from [astral.sh](https://astral.sh) offering:
  - **uv:** project management + dependency management
  - **ruff**: linter and code formatter
  - **ty**: fast type checker

Unit and integration testing is based on **pytest**.

Some commands typically used in CI pipelines:

```console
# Linting and formatting
ruff check src
ruff format src

# Type checking
ty check src

# Unit testing
uv run pytest # if the virtual env is not activated
pytest # if the virtual env is activated
```

## 5. Performance analysis

### Generating the testing file

The script `bin/generate_huge_ascii_file.py` writes a line-oriented fixed-width ASCII file from an input **COBOL copybook**.

During file generation, dandom values are chosen for 3 supported data types (`string`, `integer`, `decimal`). Significant free disk space (default output is at least **2 GiB**) will be required (/data folder is ignored by git).

In order to create a sample file, execute the following:

```console
uv run bin/generate_huge_ascii_file.py \
  test/fixtures/sample_file_record.cpy \
  data/huge_fixed_size_file.dat
```
The copybook used for generating the sample data is as follows:

```cobol
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
```

The sample file will contain around **32,540,000** records.


### Running the performance tests

From project root:

```console
uv run run.py
```
The run.py file will track the execution time of the following stages:

1. **Stage 1** — [`main()`](packages/file_validator/src/file_validator/main.py) converts the fixed-width file to an analytics-friendly Apache Parquet on disk
2. **Stage 2** — [`validation_etl`](run.py) computes all file validations according to a given set of validation rules and stores the results again on disk.

The typical execution times of each implementation are the following:

| Backend | Time (same workload, same machine) | CPU during conversion |
| --- | ---: | --- |
| **Pure Rust** (`file_validator.parsers.rust`) | **~10 s** (typical) | High utilization across cores |
| **Python using Polars** (`file_validator.parsers.polars`) | **~10 s** (typical) | High utilization across cores |

## 6. Conclusions

According to experimental results and benchmarks, the **execution wall times of both implementations are similar**.

Both implementations are able to **use 100% of the available computation resources (CPU cores)** in the testing machine used [1]. Thermal throttling may be an issue (lowering CPU frequencies specially using mainstream low-end laptop processors with limited cooling) while CPU-core temperatures are too high.

Memory consumption is stable during execution, **being able to process files larger than memory**.

Additionally, **the Python-based implementation is way simpler and more maintainable**.

**Avoid running any pure Python function as an UDFs in the polars API if performance is an goal** (expect 20-50x penalty in execution time). For coding your data transformations, use only polars expressions that are backed by rust binary execution enviroment. 

## 6. References and media

[1] htop screenshot showing CPU utilization during tests


![CPU utilization during tests](docs/cpu_utilization.png)
