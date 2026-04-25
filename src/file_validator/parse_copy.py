"""Python wrapper for Rust (PyO3) fixed-to-parquet parser."""

from __future__ import annotations

from pathlib import Path


def parse_copy(
    input_file: str | Path,
    copybook_file: str | Path,
    output_parquet_file: str | Path,
    *,
    line_terminated: bool = True,
    batch_records: int = 500_000,
    compression: str = "zstd",
) -> Path:
    """Parse fixed-size ASCII records and write a Parquet file using Rust."""
    from fixed2parquet import parse_copy_to_parquet

    input_path = Path(input_file).expanduser().resolve()
    copybook_path = Path(copybook_file).expanduser().resolve()
    output_path = Path(output_parquet_file).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not copybook_path.exists():
        raise FileNotFoundError(f"Copybook file not found: {copybook_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    parse_copy_to_parquet(
        str(input_path),
        str(copybook_path),
        str(output_path),
        line_terminated,
        batch_records,
        compression,
    )

    return output_path

