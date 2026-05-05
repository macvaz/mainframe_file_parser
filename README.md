# mainframe-validator

High-performing Python-based project for parsing fixed-width mainframe files. This is a common pattern in reg tech projects (Regulatory Technologies) applied in central banking sector.

## Goal

According to many [technical assessments](https://niklas-heer.github.io/speed-comparison/), rust is well-known as one of fastest programming languages in execution time. [Python](https://niklas-heer.github.io/speed-comparison/) is also known as one of the slowests.

The main goal of this repo is to benchmark two different implementations:
* a [Python](src/file_validator/parsers/polars/parser.py) parser (based on **polars** analytical library)
* a [Rust](rust/src/lib.rs) parser

## File parsing logic

The data pipeline is the same for both implementations:
  * Convert fixed-length file into a tabular analytical file (Parquet) and store it into disk
  * Applying a set of validation rules to the input file, geneting a new column with the validation results per applied validatin.

Both versions rely on open-source high-performing analytical libraries, enabling state-of-the-art data processing techniques like:
  * Apache Arrow
  * SIMD vectorized cpu instructions

## CI pipelines

For implementing the CI pipelines, mainstream open-source development tools are used from [astral.sh](https://astral.sh) offering:
  - **uv:** project management + dependency management
  - **ruff**: linter and code formatter
  - **ty**: fast type checker

## Performance analysis

### Generating the testing file

The script `bin/generate_huge_ascii_file.py` writes a line-oriented fixed-width ASCII file from an input **COBOL copybook**.

 Random values are chosen for 3 supported data types (`string`, `integer`, `decimal`).

**Requirements:** Enough free disk space (default output is at least **2 GiB**).

**Example** using the repository fixture copybook (65-byte payload + newline per record):

```bash
uv run bin/generate_huge_ascii_file.py \
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

The sample file will contain arround **32,540,000** records.


### Running the performance tests

From project root:

```bash
uv run run.py
```
The run.py file will track the execution time of the following stages:

1. **Stage 1** — [`main()`](src/file_validator/main.py) converts the fixed-width file to an anlytics-friedly Apache Parquet in disk
2. **Stage 2** — [`validation_etl`](run.py) computes all file validations according to a given set of validations rules and store the results again in disk.

The typical execution times of each implemetation are the following:

| Backend | Time (same workload, same machine) | CPU during conversion |
| --- | ---: | --- |
| **Pure rust** (`file_validator.parsers.rust`) | **~10 s** (typical) | High utilization across cores |
| **Python using Polars** (`file_validator.parsers.polars`) | **~10 s** (typical) | Comparable for this pipeline |

## Conclusions

According to experimental results and benchmarks, the **execution wall time of both implementations are completely aligned**.

Both implementation are able to **use 100% of the available computation resources (cpu cores)** in the testing machine used [1].

Memory consumption is stable during execution, **being able to process files bigger the memory size**.


Additionaly, **the python-based implementation is way simpler and more mantainable**. 

## Run unit and integration tests

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

## Refrences and media

[1] htop screen shot showing cpu utilization during tests


![CPU utilization during tests](docs/cpu_utilization.png)
