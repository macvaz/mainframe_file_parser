"""Polars-backed fixed-width → Parquet (no Rust extension)."""

from __future__ import annotations

from file_validator.types import MainframeParser

from .parser import parse_and_write_parquet

#: Same protocol as :data:`~file_validator.parsers.rust.file_parser`.
file_parser: MainframeParser = parse_and_write_parquet

__all__ = ["file_parser"]
