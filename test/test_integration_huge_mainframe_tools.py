from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


RECORD_SIZE = 66
SCHEMA_MAP = {
    "FULL_NAME": (0, 50, "string"),
    "YEAR": (50, 4, "integer"),
    # PIC 9(9)V99: 11 digit positions, 2 implied decimals → DECIMAL(11,2), not DECIMAL(9,2)
    # (9,2) only allows 7 integer digits before the point; full 9(9)V99 needs 11 total digits).
    "AMOUNT": (54, 11, "decimal(11,2)"),
}


@pytest.mark.huge
def test_huge_fixed_file_to_parquet_single_writer(tmp_path: Path) -> None:
    mainframe_tools = pytest.importorskip(
        "mainframe_tools",
        reason=(
            "Rust extension not installed. Build/install with "
            "bin/build_rust_extension.sh first."
        ),
    )

    root = Path(__file__).resolve().parents[1]
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
        SCHEMA_MAP,
        RECORD_SIZE,
        500_000,
    )

    shard_files = sorted(out_dir.glob("shard_*.parquet"))
    assert shard_files, (
        f"Expected shard_*.parquet under {out_dir}, "
        f"found: {sorted(p.name for p in out_dir.iterdir())}"
    )

    total_rows = sum(pq.read_metadata(p.as_posix()).num_rows for p in shard_files)
    assert total_rows == expected_rows

    amt_type = pq.read_schema(shard_files[0].as_posix()).field("AMOUNT").type
    assert amt_type == pa.decimal128(11, 2), amt_type
