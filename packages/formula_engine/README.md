# formula-engine

Evaluate validation rules and derived columns on a Polars `LazyFrame` from a small formula language (Lark grammar → Polars expressions).

## Features

- **Validations** — boolean columns (`LEN`, `BETWEEN`, comparisons)
- **Derived indicators** — numeric columns via `SUM`, `PROD`, `DIV`, and arithmetic (`+`, `-`, `*`, `/`)
- **Chained formulas** — later rules can reference earlier indicators (`{IND_A}`)
- **Column references** — input fields must use braces: `{FULL_NAME}`, `{YEAR}`

## Install

From the monorepo root:

```console
uv sync --all-packages
```

## Usage

```python
from pathlib import Path

import polars as pl
from formula_engine import compute

lf = pl.scan_parquet("data/parsed.parquet")
result = compute(Path("formulas.txt"), lf)
result.sink_parquet("data/with_formulas.parquet")
```

Example `formulas.txt`:

```text
VALID_NAME: LEN({FULL_NAME}) == 9
VALID_YEAR: BETWEEN({YEAR}, 1900, 2026)
IND_AMOUNT_PLUS_YEAR: SUM({AMOUNT}, {YEAR})
IND_DOUBLE: PROD({IND_AMOUNT_PLUS_YEAR}, 2)
```

Public API:

| Symbol | Description |
|--------|-------------|
| `compute` | Load formulas from a file path and append columns to a `LazyFrame` |
| `parse_formulas` | Parse formula text → list of named Polars expressions |
| `FormulaSyntaxError` | Invalid syntax or bare column name without `{…}` |

### Supported functions

| Function | Description |
|----------|-------------|
| `LEN({col})` | String byte length |
| `BETWEEN({col}, low, high)` | Inclusive range check |
| `SUM(...)`, `PROD(...)`, `DIV(...)` | Numeric aggregation / fold |

## Layout

```
src/formula_engine/
├── engine.py            # compute, parse_formulas
├── grammar/             # Lark grammar + Polars transformer
├── graph/               # DAG execution order
└── common/types.py
tests/
└── fixtures/            # sample formula files for unit tests
```

## Tests

```console
uv run pytest packages/formula_engine/tests/
```
