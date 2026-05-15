"""Rust ``mainframe_tools`` extension as :class:`~file_validator.types.MainframeParser`."""

from __future__ import annotations

import mainframe_tools

from file_validator.types import MainframeParser

#: Compiled extension entrypoint; see :class:`~file_validator.types.MainframeParser`.
file_parser: MainframeParser = mainframe_tools.parse_and_write_parquet

__all__ = ["file_parser"]
