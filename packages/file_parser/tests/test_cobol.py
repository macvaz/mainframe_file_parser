from __future__ import annotations

from pathlib import Path

import pytest

from file_parser import get_schema_from_copybook
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


def test_get_schema_from_copybook_skips_comments_and_blank_lines() -> None:
    copybook = """
      * comment line
      /
           05  FLAG   PIC X(1).
    """
    cols = get_schema_from_copybook(copybook)
    assert len(cols) == 1
    assert cols[0].name == "FLAG"


def test_pic_info_to_column_unsupported_type() -> None:
    from file_parser.utils.cobol import _pic_info_to_column

    with pytest.raises(ValueError, match="unsupported PIC"):
        _pic_info_to_column(
            "BAD",
            0,
            {"type": "Signed Packed", "length": 5, "precision": 0},
        )


def test_pic_info_to_column_float() -> None:
    from file_parser.utils.cobol import _pic_info_to_column

    col = _pic_info_to_column(
        "RATE",
        10,
        {"type": "Float", "length": 8, "precision": 2},
    )
    assert col == ColumnDefinition("RATE", 10, 8, "decimal", precision=8, scale=2)
