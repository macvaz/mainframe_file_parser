from __future__ import annotations

import tempfile
from pathlib import Path

import pyarrow.parquet as pq
import pytest


RECORD_SIZE = 66
SCHEMA_MAP = {
    "FULL_NAME": (0, 50, "string"),
    "YEAR": (50, 4, "integer"),
    "AMOUNT": (54, 11, "integer"),
}


@pytest.mark.huge
def test_huge_fixed_file_to_parquet_shards() -> None:
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

    out_dir = Path(tempfile.mkdtemp(prefix="huge_parquet_shards_"))
    mainframe_tools.parse_and_write_parquet(
        str(input_path),
        str(out_dir),
        SCHEMA_MAP,
        RECORD_SIZE,
        500_000,
    )

    shards = sorted(out_dir.glob("shard_*.parquet"))
    assert shards, "No parquet shards generated."

    total_rows = 0
    for shard in shards:
        total_rows += pq.read_metadata(shard.as_posix()).num_rows

    assert total_rows == expected_rows

