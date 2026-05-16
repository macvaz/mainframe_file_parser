"""Shared types for fixed-width record parsers (Rust ``mainframe_tools`` and Polars)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeAlias


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    start: int
    length: int
    kind: str
    precision: int | None = None
    scale: int | None = None


FileSchema: TypeAlias = list[ColumnDefinition]


class MainframeParser(Protocol):
    """Parses a fixed-width file into Snappy Parquet (one or more files under a folder).

    The Rust backend writes ``shard_*.parquet`` parts; the Polars backend writes a
    single ``data.parquet``. Each backend exposes ``file_parser`` from its package,
    for example ``from file_parser.parsers.rust import file_parser`` or
    ``from file_parser.parsers.polars import file_parser``.
    """

    def __call__(
        self,
        input_path: str,
        output_folder: str,
        schema: FileSchema,
        record_size: int,
        rows_per_batch: int,
    ) -> None: ...


__all__ = [
    "ColumnDefinition",
    "FileSchema",
    "MainframeParser",
]
