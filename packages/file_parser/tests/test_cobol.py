from __future__ import annotations

from pathlib import Path

import pytest

from file_parser.utils.cobol import get_schema_from_copybook
from file_parser.types import ColumnDefinition

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_file_record.cpy"


def test_get_schema_from_copybook_file_matches_run_py_schema() -> None:
    cols = get_schema_from_copybook(FIXTURE)
    assert cols == [
        ColumnDefinition("FULL_NAME", 0, 50, "string", None, None),
        ColumnDefinition("YEAR", 50, 4, "integer", None, None),
        ColumnDefinition("AMOUNT", 54, 11, "decimal", 11, 2),
    ]
    assert get_schema_from_copybook(FIXTURE.read_text(encoding="utf-8")) == cols


def test_get_schema_from_copybook_empty_raises() -> None:
    with pytest.raises(ValueError, match="no elementary PIC"):
        get_schema_from_copybook("* empty\n")
