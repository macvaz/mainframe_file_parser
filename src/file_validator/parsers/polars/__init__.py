"""Polars-backed fixed-width → Parquet (no Rust extension)."""

from __future__ import annotations

from file_validator.types import MainframeParser

from .parser import parse_and_write_parquet

file_parser: MainframeParser = parse_and_write_parquet

__all__ = ["file_parser"]
