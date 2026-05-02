"""Shared types for fixed-width record parsers (Rust ``mainframe_tools`` and Polars)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

ColumnSpec: TypeAlias = tuple[int, int, str]
FileSchema: TypeAlias = Mapping[str, ColumnSpec]


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    start: int
    length: int
    kind: str
    precision: int | None = None
    scale: int | None = None


class MainframeParser(Protocol):
    """Parses a fixed-width file into Snappy Parquet (one or more files under a folder).

    The Rust backend writes ``shard_*.parquet`` parts; the Polars backend writes a
    single ``data.parquet``. Each backend exposes ``file_parser`` from its package,
    for example ``from file_validator.parsers.rust import file_parser`` or
    ``from file_validator.parsers.polars import file_parser``.
    """

    def __call__(
        self,
        input_path: str,
        output_folder: str,
        schema_dict: FileSchema,
        record_size: int,
        rows_per_batch: int,
    ) -> None: ...


__all__ = [
    "ColumnDefinition",
    "ColumnSpec",
    "FileSchema",
    "MainframeParser",
]
