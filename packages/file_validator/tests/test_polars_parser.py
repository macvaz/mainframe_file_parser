from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from file_validator.parsers.polars.utils import parse_file_according_to_schema
from file_validator.utils.cobol import get_schema_from_copybook

_COPYBOOK = """
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
"""


def test_parse_implied_decimal_amount(tmp_path: Path) -> None:
    schema = get_schema_from_copybook(_COPYBOOK)
    # payload: 50-char name, year 2024, amount 272956798.27 as 27295679827
    name = "A" * 50
    line = f"{name}202427295679827\n"
    data_file = tmp_path / "sample.dat"
    data_file.write_text(line, encoding="ascii")

    df = parse_file_according_to_schema(data_file, schema).collect()

    assert df["YEAR"].item() == 2024
    assert df["AMOUNT"].item() == Decimal("272956798.27")


def test_parse_decimal_invalid_becomes_null(tmp_path: Path) -> None:
    schema = get_schema_from_copybook(_COPYBOOK)
    name = "B" * 50
    line = f"{name}2024NOT_A_NUM11\n"
    data_file = tmp_path / "bad.dat"
    data_file.write_text(line, encoding="ascii")

    df = parse_file_according_to_schema(data_file, schema).collect()

    assert df["AMOUNT"].item() is None
