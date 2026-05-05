"""Scan parser Parquet output as a Polars LazyFrame (public export for :mod:`file_validator`)."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from file_validator.utils.file_utils import scan_parquet_output


def read_parquet(output_path: str | Path) -> pl.LazyFrame:
    return scan_parquet_output(Path(output_path))


__all__ = ["read_parquet"]
