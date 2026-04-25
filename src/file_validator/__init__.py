"""file_validator package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["parse_copy", "read_parquet"]


def __getattr__(name: str) -> Any:
    if name == "parse_copy":
        from .parse_copy import parse_copy

        return parse_copy
    if name == "read_parquet":
        from .scan_parquet import read_parquet

        return read_parquet
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from .parse_copy import parse_copy as parse_copy
    from .scan_parquet import read_parquet as read_parquet
