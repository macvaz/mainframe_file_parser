from __future__ import annotations

from pathlib import Path
from typing import cast

import polars as pl

from file_parser.main import parse
from file_parser.parsers.polars import file_parser as polars_file_parser
from file_parser.types import ColumnDefinition
from file_parser.utils import PARQUET_OUTPUT_FILENAME, get_total_length

_SCHEMA: list[ColumnDefinition] = [
    ColumnDefinition("FIELD", 0, 4, "string", None, None),
]


def _write_fixed_file(path: Path, line: str) -> None:
    path.write_text(line if line.endswith("\n") else f"{line}\n", encoding="ascii")


def test_parse_writes_parquet_when_missing(tmp_path: Path) -> None:
    data = tmp_path / "in.dat"
    out = tmp_path / "out"
    _write_fixed_file(data, "ABCD")

    lf = parse(data, out, _SCHEMA, polars_file_parser)
    df = cast(pl.DataFrame, lf.collect())

    assert df["FIELD"].to_list() == ["ABCD"]
    assert (out / PARQUET_OUTPUT_FILENAME).is_file()
    record_size = get_total_length(_SCHEMA, line_terminated=True)
    assert record_size == 5


def test_parse_reuses_existing_parquet(tmp_path: Path) -> None:
    data = tmp_path / "in.dat"
    out = tmp_path / "out"
    _write_fixed_file(data, "WXYZ")
    parse(data, out, _SCHEMA, polars_file_parser)

    def fail_parser(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("parser must not run when parquet output already exists")

    lf = parse(data, out, _SCHEMA, fail_parser)
    assert cast(pl.DataFrame, lf.collect())["FIELD"].to_list() == ["WXYZ"]
