"""Shared types for fixed-width record parsers (Rust ``mainframe_tools`` and Polars)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, TypeAlias

# Per-column layout: ``(byte_offset, length)`` implies string;
# ``(byte_offset, length, type)`` adds the logical type (same strings in Rust and Polars).
UntypedColumnSpec: TypeAlias = tuple[int, int]
TypedColumnSpec: TypeAlias = tuple[int, int, str]
ColumnSpec: TypeAlias = UntypedColumnSpec | TypedColumnSpec

# Maps output column names to layout tuples (insertion order defines column order).
FixedWidthSchema: TypeAlias = Mapping[str, ColumnSpec]


class MainframeParser(Protocol):
    """Parses a fixed-width file into sharded Snappy Parquet (``shard_*.parquet``).

    Each backend exposes ``file_parser`` from its package, for example
    ``from file_validator.parsers.rust import file_parser`` or
    ``from file_validator.parsers.polars import file_parser``.
    """

    def __call__(
        self,
        input_path: str,
        output_folder: str,
        schema_dict: FixedWidthSchema,
        record_size: int,
        rows_per_batch: int,
    ) -> None: ...


__all__ = [
    "ColumnSpec",
    "FixedWidthSchema",
    "MainframeParser",
    "TypedColumnSpec",
    "UntypedColumnSpec",
]
