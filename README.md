# mainframe-validator

A high-performance Python tool for **parsing fixed-width ASCII mainframe files** based on **COBOL copybooks**. This is a common pattern in Regtech projects (Regulatory Technologies) used in the central banking industry.

Additionaly, the received input file is validated using a **set of declarative validation formulas** written externally using an **ad-hoc DSL (domain-specific language)**.

## 1. Goal

According to many [technical assessments](https://niklas-heer.github.io/speed-comparison/), Rust is well known as one of the fastest programming languages in terms of execution time. Python is also known as one of the slowest.

The main goal of this repo is to benchmark two different implementations:
* a [Python](packages/file_parser/src/file_parser/parsers/polars/parser.py) parser (based on the [Polars](https://github.com/pola-rs/polars) analytical library)
* a [Rust](packages/file_parser/rust/src/lib.rs) parser developed from scratch

Both versions rely on high-performance open-source analytical libraries, enabling state-of-the-art data processing techniques such as:
  * Apache Arrow
  * SIMD vectorized CPU instructions

## 2. Project structure and setup

The project is structured as a monorepo. Several Python packages live under the [packages](packages/) folder.

For readability, the most relevant project folders and files are highlighted in the following structure:

```diff
 mainframe_validator/
+├── .cursor/                         # Cursor skills for AI code assistants  
+├── .github/                         # GitHub Actions CI pipelines  
+├── .pre-commit-config.yaml          # Local hooks (ruff, ty, pytest; mirrors CI)
 ├── bin/
 ├── data/                            # Data files (gitignored)
 ├── docs/
 ├── notebooks/
+├── packages/                        # Monorepo packages
+│   ├── file_parser/                 # Fixed-length file parser from a COBOL copybook
 │   │   ├── rust/
 │   │   │   └── src/lib.rs           # Rust extension code
 │   │   ├── src/file_parser/
 │   │   │   ├── main.py
 │   │   │   ├── parsers/
 │   │   │   │   ├── polars/          # Polars-based parser
 │   │   │   │   │   ├── parser.py
 │   │   │   │   │   └── utils.py
 │   │   │   │   └── rust/            # Python bindings to Rust extension
 │   │   │   ├── types/
 │   │   │   └── utils/
 │   │   ├── tests/
 │   │   └── typings/mainframe_tools/
+│   └── formula_engine/              # Formula language for validations (and derived data)
 │       ├── src/formula_engine/
 │       │   ├── engine.py
 │       │   ├── grammar/
 │       │   └── graph/
 │       └── tests/
 ├── conftest.py
+├── formulas.txt                     # Formulas executed by benchmark.py
 ├── pyproject.toml                   # Workspace root (uv)
+├── benchmark.py                     # Benchmark entrypoint
 └── uv.lock
```

The project is managed with **uv**. To create the Python virtual environment and install dependencies for all packages, run:

```console
uv sync --all-packages --group dev
```

Modern IDEs will automatically activate the virtual environment. Otherwise, activate it manually:

```console
source .venv/bin/activate
```

### Laptop installation on a locked-down corporate network

The installation process differs if you work for a company with **strict security policies** where direct access to pypi.org is not allowed. Additionally, uv will not be able to install Python interpreters either.

Under these conditions, a professional, corporate-ready deployment setup is as follows:
* Install [miniforge](https://github.com/conda-forge/miniforge) following your employer's installation procedure
* Create a Python 3.12 mamba environment
* Install uv
* Create the project's uv virtual environment using the mamba environment
* Configure `pyproject.toml` to point to a private package index
* Resolve dependencies with uv

The complete corporate workflow is as follows:

1. Install the Python interpreter and uv:
```console
mamba create -n mainframe_validator python=3.12 -y   
mamba activate mainframe_validator
mamba install -c conda-forge uv
```

2. Point uv to your local Artifactory by editing [pyproject.toml](pyproject.toml) and adding this section:

```toml
[[tool.uv.index]]
name = "corp-artifactory"
url = "https://artifactory.corp.example/artifactory/api/pypi/pypi-virtual/simple"
default = true
```

3. Install dependencies with uv:  

```console
cd <your_local_path_to_repo>/mainframe_validator
uv venv --python "3.12"
uv sync --all-packages --group dev
source .venv/bin/activate
```

Sometimes, depending on **local security group policies**, uv will not run unless the project code is in a designated folder such as `D:\custom_tools`. In that case, clone or copy the repository into that folder.

## 3. CI pipelines

CI pipelines use mainstream open-source tools from [astral.sh](https://astral.sh):
  - **uv**: project management and dependency management
  - **ruff**: linter and code formatter
  - **ty**: fast type checker

Unit and integration tests use **pytest**.

With the virtual environment activated, these commands match what CI runs:

```console
# Linting and formatting
ruff check .
ruff format .

# Type checking
ty check .

# Unit testing
pytest
```

Running these commands manually before every commit is inconvenient. Install an automated local CI pipeline with **pre-commit** as follows:

```console
uv run pre-commit install
```

After installing the Git hooks, each commit in your development environment **automatically triggers the local CI pipeline**, for example:

```console
ruff check...............................................................Passed
ruff format (check)......................................................Passed
ty check.................................................................Passed
pytest...................................................................Passed
```

Additionally, a server-side CI pipeline runs on [GitHub Actions](https://github.com/macvaz/mainframe_file_parser/actions).

## 4. Functional scope

Starting from a [COBOL copybook](https://www.ibm.com/docs/en/cics-ts/5.5.0?topic=books-cobol-copy), both parser implementations will execute the same data transformations:
  * **Parse the fixed-width file** according to the **copybook**, convert it to a tabular analytics file (Parquet), and store it on disk
  * **Apply validation formulas** from the [formula language](formulas.txt) to that Parquet data, adding one column per formula

The sample copybook is:

```cobol
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
```

The resulting DataFrame has two main parts:
  - One column per field defined in the copybook (FULL_NAME, YEAR and AMOUNT)
  - One column per validation formula defined in the [formulas.txt](formulas.txt) file (VALID_NAME, VALID_YEAR, VALID_AMOUNT)

Sample declarative validation formulas:

```SQL
VALID_NAME: LEN({FULL_NAME}) == 9
VALID_YEAR: BETWEEN({YEAR}, 1900, 2026)
VALID_AMOUNT: BETWEEN({AMOUNT}, 0, 672581176.44)
```

The expected results are shown in the screenshot below:

![Resulting dataframe](docs/resulting_dataframe.jpg)

**Jupyter notebooks** are recommended for quick experimentation. Use [this notebook](notebooks/exploration.ipynb) to explore the project interactively.

## 5. Performance analysis

### Generating a test data file

The script `bin/generate_huge_ascii_file.py` writes a line-oriented fixed-width ASCII file from an input **COBOL copybook**.

During file generation, random values are chosen for three supported data types (`string`, `integer`, `decimal`). Ensure sufficient free disk space (the default output is at least **2 GiB**; the `data/` folder is gitignored).

To create a sample file, run:

```console
uv run bin/generate_huge_ascii_file.py \
  test/fixtures/sample_file_record.cpy \
  data/huge_fixed_size_file.dat
```

The sample file will contain around **32,540,000** records.

If the data file uses a name other than **`huge_fixed_size_file`**, set the following environment variable:

```console
# Don't set the file extension or the path, just the name
# Default value is "huge_fixed_size_file"
export MAINFRAME_FILE_STEM=<name_of_data_file> 
```


### Running the performance tests

From the project root:

```console
uv run benchmark.py
```

The `benchmark.py` script measures execution time for these stages:

1. **Stage 1** — [`parse()`](packages/file_parser/src/file_parser/main.py) converts the fixed-width file to analytics-friendly Apache Parquet on disk
2. **Stage 2** — [`compute()`](packages/formula_engine/src/formula_engine/engine.py) applies `formulas.txt` (validations and derived columns) and writes the results to disk

Typical execution times for each implementation are:

| Backend | Time (same workload, same machine) | CPU usage   |
| --- | ---: | --- |
| **Pure Rust** | **~10 s** (typical) | High utilization across cores |
| **Python using Polars** | **~10 s** (typical) | High utilization across cores |

## 6. Conclusions

According to experimental results and benchmarks, the **execution wall times of both implementations are similar**.

Both implementations can **saturate available CPU cores** on the test machine [1]. Thermal throttling may occur (especially on mainstream laptops with limited cooling), lowering CPU frequency when core temperatures stay high.

Memory consumption stays stable during execution, so the tool **can process files larger than available RAM**.

Additionally, **the Python-based implementation is much simpler and more maintainable**.

**Avoid pure Python UDFs in the Polars API when performance matters** (expect a 20–50× slowdown). Implement transformations with Polars expressions that run in Polars’ Rust execution engine.

## 7. References and media

[1] htop screenshot showing CPU utilization during tests


![CPU utilization during tests](docs/cpu_utilization.png)
