"""file_parser package."""

from __future__ import annotations

from .main import parse
from .utils import get_schema_from_copybook

__all__ = [
    "parse",
    "get_schema_from_copybook",
]
