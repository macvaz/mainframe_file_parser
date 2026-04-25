from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import pytest

pl = pytest.importorskip("polars")


RECORD_LEN = 66  # 50 + 4 + 11 + newline, same as bin/generate_huge_ascii_file.py


@pytest.mark.huge
def test_rust_converter_huge_fixed_file_to_parquet(tmp_path: Path) -> None:
    """Multi-GB fixture; not collected unless you pass ``pytest --run-huge``."""
    pytest.importorskip(
        "fixed2parquet",
        reason=(
            "Rust wheel not installed. See README: maturin build + "
            "uv pip install rust/target/wheels/fixed2parquet-*.whl"
        ),
    )

    root = Path(__file__).resolve().parents[1]
    input_path = root / "data" / "huge_fixed_size_file.dat"
    copybook_path = root / "schema" / "sample.cpy"
    parquet_path = tmp_path / "huge_out.parquet"

    if not input_path.is_file():
        pytest.skip(f"Huge fixture missing: {input_path}")
    if not copybook_path.is_file():
        pytest.skip(f"Copybook missing: {copybook_path}")

    size = input_path.stat().st_size
    if size % RECORD_LEN != 0:
        pytest.fail(
            f"Unexpected file size {size}; not divisible by record length {RECORD_LEN}"
        )
    expected_rows = size // RECORD_LEN

    import file_validator.parse_copy as parse_copy_module

    result_path = parse_copy_module.parse_copy(
        input_file=input_path,
        copybook_file=copybook_path,
        output_parquet_file=parquet_path,
        line_terminated=True,
        batch_records=500_000,
    )

    assert result_path == parquet_path.resolve()
    assert parquet_path.is_file()

    meta = pq.read_metadata(parquet_path.as_posix())
    assert meta.num_rows == expected_rows

    schema = pl.scan_parquet(parquet_path).collect_schema()
    assert list(schema.names()) == ["FULL_NAME", "YEAR", "AMOUNT"]
