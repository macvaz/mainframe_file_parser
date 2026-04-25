"""Read a Parquet file in columnar mode using Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl


def read_parquet(path: str | Path) -> pl.LazyFrame:
    """Read a full parquet file and return a DataFrame."""
    return pl.scan_parquet(path)



