from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import polars as pl
import pytest

from file_parser import get_schema_from_copybook
from file_parser.parsers.polars import file_parser as polars_file_parser
from file_parser.parsers.polars.utils import (
    _polars_dtype,
    column_exprs_from_schema,
    parse_file_according_to_schema,
)
from file_parser.types import ColumnDefinition
from file_parser.utils import PARQUET_OUTPUT_FILENAME

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

    df = cast(pl.DataFrame, parse_file_according_to_schema(data_file, schema).collect())

    assert df["YEAR"].item() == 2024
    assert df["AMOUNT"].item() == Decimal("272956798.27")


def test_parse_decimal_invalid_becomes_null(tmp_path: Path) -> None:
    schema = get_schema_from_copybook(_COPYBOOK)
    name = "B" * 50
    line = f"{name}2024NOT_A_NUM11\n"
    data_file = tmp_path / "bad.dat"
    data_file.write_text(line, encoding="ascii")

    df = cast(pl.DataFrame, parse_file_according_to_schema(data_file, schema).collect())

    assert df["AMOUNT"].item() is None


def test_column_exprs_float_and_decimal_scale_zero() -> None:
    float_schema = [ColumnDefinition("VALUE", 0, 6, "float", None, None)]
    lf = pl.LazyFrame({"raw": ["123.45"]})
    float_df = cast(
        pl.DataFrame,
        lf.with_columns(column_exprs_from_schema("raw", float_schema)).collect(),
    )
    assert float_df["VALUE"].item() == pytest.approx(123.45)

    scale_zero_schema = [
        ColumnDefinition("UNITS", 0, 4, "decimal", precision=4, scale=0)
    ]
    lf2 = pl.LazyFrame({"raw": ["0042"]})
    scale_df = cast(
        pl.DataFrame,
        lf2.with_columns(column_exprs_from_schema("raw", scale_zero_schema)).collect(),
    )
    assert scale_df["UNITS"].item() == 42


def test_polars_dtype_helpers() -> None:
    assert (
        _polars_dtype(ColumnDefinition("S", 0, 1, "string", None, None)) == pl.String()
    )
    assert (
        _polars_dtype(ColumnDefinition("I", 0, 1, "integer", None, None)) == pl.Int64()
    )
    assert (
        _polars_dtype(ColumnDefinition("F", 0, 1, "float", None, None)) == pl.Float64()
    )
    assert _polars_dtype(
        ColumnDefinition("D", 0, 4, "decimal", precision=4, scale=2)
    ) == pl.Decimal(4, 2)
    exprs = column_exprs_from_schema(
        "raw",
        [ColumnDefinition("I", 0, 2, "integer", None, None)],
    )
    assert len(exprs) == 1


def test_parse_and_write_parquet(tmp_path: Path) -> None:
    schema = get_schema_from_copybook(_COPYBOOK)
    name = "C" * 50
    data_file = tmp_path / "lines.dat"
    data_file.write_text(f"{name}199910000000000\n", encoding="ascii")
    out_dir = tmp_path / "parquet_out"
    polars_file_parser(
        str(data_file),
        str(out_dir),
        schema,
        record_size=65,
        rows_per_batch=100,
    )
    assert (out_dir / PARQUET_OUTPUT_FILENAME).is_file()
