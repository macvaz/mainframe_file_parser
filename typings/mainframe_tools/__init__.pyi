"""Type stubs for the ``mainframe_tools`` Rust extension (see ``rust/src/lib.rs``).

``schema`` must match ``file_validator.types.FileSchema``: an ordered list of
:class:`~file_validator.types.ColumnDefinition`.
"""

from __future__ import annotations

from file_validator.types import FileSchema


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
