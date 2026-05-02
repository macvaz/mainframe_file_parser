"""Helpers for fixed-width layouts and Parquet paths."""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl

from file_validator.types import FixedWidthSchema


def get_total_length(schema: FixedWidthSchema, *, line_terminated: bool = False) -> int:
    """Fixed bytes per record from column layout ``(offset, length[, type])``.

    Returns ``max(offset + length)`` over all fields. If records end with a
    line-feed after the payload (typical for generated ASCII fixtures), pass
    ``line_terminated=True`` to add one byte.
    """
    max_end = 0
    for name, spec in schema.items():
        if not isinstance(spec, tuple) or len(spec) < 2:
            raise TypeError(
                f"schema[{name!r}] must be a tuple (offset, length) or (offset, length, type)"
            )
        start, length = int(spec[0]), int(spec[1])
        if start < 0 or length < 0:
            raise ValueError(
                f"schema[{name!r}]: offset and length must be non-negative"
            )
        max_end = max(max_end, start + length)
    return max_end + (1 if line_terminated else 0)


def scan_parquet_output(output_path: Path) -> pl.LazyFrame:
    """Scan a single Parquet file or a directory of ``shard_*.parquet`` parts."""
    if output_path.is_dir():
        return pl.scan_parquet(str(output_path / "shard_*.parquet"))
    return pl.scan_parquet(str(output_path))


def remove_file_or_tree(path: str | Path) -> None:
    """Remove a file or directory tree at ``path`` if it exists; no-op if missing."""
    p = Path(path)
    if p.is_dir():
        shutil.rmtree(p)
    elif p.is_file():
        p.unlink()
