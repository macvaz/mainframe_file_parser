# file-parser

Parse fixed-width mainframe files defined by a COBOL copybook into Polars-friendly Parquet, using either a Polars-based parser or an optional Rust extension.

## Features

- Build a fixed-width **schema** from a COBOL copybook (`PIC` clauses)
- Convert line-oriented ASCII files to **Parquet**
- Two parser backends:
  - **Polars** — pure Python/Polars, no native build
  - **Rust** (`mainframe_tools`) — PyO3 + Arrow/Parquet for higher throughput

## Install

From the monorepo root:

```console
uv sync --all-packages
```

To build the Rust parser:

```console
./bin/build_rust_extension.sh
```

## Usage

```python
from file_parser import get_schema_from_copybook, parse
from file_parser.parsers.polars import file_parser

copybook = """
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
"""

schema = get_schema_from_copybook(copybook)
lf = parse(
    "data/input.dat",
    "data/output.parquet",
    schema,
    file_parser,
)
```

Public API:

| Symbol | Description |
|--------|-------------|
| `get_schema_from_copybook` | Copybook text or path → column layout |
| `parse` | Fixed-width file → Parquet (if needed) → `LazyFrame` |

## Layout

```
src/file_parser/
├── main.py              # parse()
├── types/               # ColumnDefinition, FileSchema
├── utils/               # COBOL schema, Parquet I/O
└── parsers/
    ├── polars/          # Polars scan_csv + expressions
    └── rust/            # mainframe_tools bindings
rust/                    # Rust extension source
tests/
```

## Tests

```console
uv run pytest packages/file_parser/tests/
```

Huge-file integration tests require `--run-huge` (see root `conftest.py`).
