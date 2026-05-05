"""COBOL copybook → fixed-width schema (public export for :mod:`file_validator`)."""

from __future__ import annotations

from file_validator.utils.cobol import get_schema_from_copybook as parse_copy

__all__ = ["parse_copy"]
