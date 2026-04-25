from __future__ import annotations

from pathlib import Path

import pytest

pl = pytest.importorskip("polars")


def _build_record(full_name: str, year: int, amount_raw: int) -> str:
    # Same schema as the huge file:
    # FULL_NAME PIC A(50), YEAR PIC 9(4), AMOUNT PIC 9(9)V99 (11 digits)
    return f"{full_name[:50].ljust(50)}{year:04d}{amount_raw:011d}\n"


def test_rust_converter_small_fixed_file_to_parquet(tmp_path: Path) -> None:
    pytest.importorskip(
        "fixed2parquet",
        reason=(
            "Rust wheel not installed. From repo root: "
            "maturin build --manifest-path rust/Cargo.toml -o rust/target/wheels && "
            "uv pip install --python .venv/bin/python --reinstall --no-deps "
            "rust/target/wheels/fixed2parquet-*.whl"
        ),
    )
    import file_validator.parse_copy as parse_copy_module

    input_path = tmp_path / "small_fixed.dat"
    copybook_path = tmp_path / "layout.cpy"
    parquet_path = tmp_path / "out.parquet"

    copybook_path.write_text(
        "\n".join(
            [
                "       01 RECORD-LAYOUT.",
                "          05 FULL_NAME           PIC A(50).",
                "          05 YEAR                PIC 9(4).",
                "          05 AMOUNT              PIC 9(9)V99.",
            ]
        )
        + "\n",
        encoding="ascii",
    )

    input_path.write_text(
        "".join(
            [
                _build_record("ALICE DOE", 2024, 12345678901),
                _build_record("BOB SMITH", 1999, 1),
                _build_record("CAROL JONES", 2007, 42),
            ]
        ),
        encoding="ascii",
    )

    result_path = parse_copy_module.parse_copy(
        input_file=input_path,
        copybook_file=copybook_path,
        output_parquet_file=parquet_path,
        line_terminated=True,
        batch_records=1000,
    )

    assert result_path == parquet_path.resolve()
    assert parquet_path.exists()

    df = pl.read_parquet(result_path)
    assert df.shape == (3, 3)
    assert df.columns == ["FULL_NAME", "YEAR", "AMOUNT"]

    rows = df.to_dicts()
    assert rows == [
        {"FULL_NAME": "ALICE DOE", "YEAR": 2024, "AMOUNT": 12345678901},
        {"FULL_NAME": "BOB SMITH", "YEAR": 1999, "AMOUNT": 1},
        {"FULL_NAME": "CAROL JONES", "YEAR": 2007, "AMOUNT": 42},
    ]

