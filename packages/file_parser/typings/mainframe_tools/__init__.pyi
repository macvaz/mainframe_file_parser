"""Type stubs for the ``mainframe_tools`` Rust extension (see ``rust/src/lib.rs``).

``schema`` must match ``file_parser.types.FileSchema``: an ordered list of
:class:`~file_parser.types.ColumnDefinition`.
"""

from __future__ import annotations

from file_parser.types import FileSchema

def parse_and_write_parquet(
    input_path: str,
    output_folder: str,
    schema: FileSchema,
    record_size: int,
    rows_per_batch: int,
) -> None:
    """Slice fixed-width records using ``ColumnDefinition.start`` / ``length`` / ``kind``."""
    ...

__all__ = ["parse_and_write_parquet"]
