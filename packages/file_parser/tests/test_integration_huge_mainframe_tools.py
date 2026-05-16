from __future__ import annotations

from pathlib import Path
from typing import cast

import polars as pl
import pytest

from file_parser.types import ColumnDefinition

RECORD_SIZE = 66
# Same layout as benchmark.py / copybook: PIC 9(9)V99 → 11 positions, 2 implied decimals.
SCHEMA: list[ColumnDefinition] = [
    ColumnDefinition("FULL_NAME", 0, 50, "string", None, None),
    ColumnDefinition("YEAR", 50, 4, "integer", None, None),
    ColumnDefinition("AMOUNT", 54, 11, "decimal", 11, 2),
]


@pytest.mark.huge
def test_huge_fixed_file_to_parquet_single_writer(tmp_path: Path) -> None:
    mainframe_tools = pytest.importorskip(
        "mainframe_tools",
        reason=(
            "Rust extension not installed. Build/install with "
            "bin/build_rust_extension.sh first."
        ),
    )

    root = Path(__file__).resolve().parents[3]
    input_path = root / "data" / "huge_fixed_size_file.dat"
    if not input_path.is_file():
        pytest.skip(f"Huge input file not found: {input_path}")

    file_size = input_path.stat().st_size
    assert file_size % RECORD_SIZE == 0
    expected_rows = file_size // RECORD_SIZE

    out_dir = tmp_path / "parquet"
    mainframe_tools.parse_and_write_parquet(
        str(input_path),
        str(out_dir),
        SCHEMA,
        RECORD_SIZE,
        500_000,
    )

    shard_files = sorted(out_dir.glob("shard_*.parquet"))
    assert shard_files, (
        f"Expected shard_*.parquet under {out_dir}, "
        f"found: {sorted(p.name for p in out_dir.iterdir())}"
    )

    total_rows = cast(
        pl.DataFrame,
        pl.scan_parquet([p.as_posix() for p in shard_files]).select(pl.len()).collect(),
    ).item()
    assert total_rows == expected_rows

    amt_dtype = pl.scan_parquet(shard_files[0].as_posix()).collect_schema()["AMOUNT"]
    assert amt_dtype == pl.Decimal(11, 2), amt_dtype
