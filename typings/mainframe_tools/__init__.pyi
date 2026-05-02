"""Type stubs for the ``mainframe_tools`` Rust extension (see ``rust/src/lib.rs``)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Tuple, TypeAlias, Union

_Untyped: TypeAlias = Tuple[int, int]
_Typed: TypeAlias = Tuple[int, int, str]
ColumnSpec: TypeAlias = Union[_Untyped, _Typed]

def parse_and_write_parquet(
    input_path: str,
    output_folder: str,
    schema_dict: Mapping[str, ColumnSpec],
    record_size: int,
    rows_per_batch: int,
) -> None: ...

__all__ = ["parse_and_write_parquet"]
