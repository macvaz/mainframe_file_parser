"""Helpers for fixed-width layouts and Parquet paths."""

from __future__ import annotations

import shutil
from pathlib import Path

import polars as pl

from file_parser.types import FileSchema

# Single Snappy Parquet file written by the Polars parser (not Rust shard parts).
PARQUET_OUTPUT_FILENAME = "data.parquet"


def get_total_length(schema: FileSchema, *, line_terminated: bool = False) -> int:
    """Fixed bytes per record from a :class:`~file_parser.types.FileSchema` layout.

    ``FileSchema`` is an ordered list of :class:`~file_parser.types.ColumnDefinition`.
    Returns ``max(start + length)`` over all columns. If records end with a line-feed
    after the payload (typical for generated ASCII fixtures), pass
    ``line_terminated=True`` to add one byte.
    """
    max_end = 0
    for col in schema:
        if col.start < 0 or col.length < 0:
            raise ValueError(
                f"schema column {col.name!r}: start and length must be non-negative"
            )
        max_end = max(max_end, col.start + col.length)
    return max_end + (1 if line_terminated else 0)


def scan_parquet_output(output_path: str | Path) -> pl.LazyFrame:
    """Scan parser output: a Parquet file path, or a directory.

    Directories may contain Rust ``shard_*.parquet`` parts or a single Polars
    ``data.parquet`` file (see :data:`PARQUET_OUTPUT_FILENAME`).
    """
    output_path = Path(output_path)
    if output_path.is_dir():
        if any(output_path.glob("shard_*.parquet")):
            return pl.scan_parquet(str(output_path / "shard_*.parquet"))
        single = output_path / PARQUET_OUTPUT_FILENAME
        if single.is_file():
            return pl.scan_parquet(str(single))
        raise FileNotFoundError(
            f"No Parquet output found under {output_path}: "
            f"expected shard_*.parquet or {PARQUET_OUTPUT_FILENAME}"
        )
    return pl.scan_parquet(str(output_path))


def remove_file_or_tree(path: str | Path) -> None:
    """Remove a file or directory tree at ``path`` if it exists; no-op if missing."""
    p = Path(path)
    if p.is_dir():
        shutil.rmtree(p)
    elif p.is_file():
        p.unlink()
