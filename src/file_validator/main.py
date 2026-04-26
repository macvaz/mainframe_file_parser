"""Convert fixed-width input to Parquet and scan results with Polars."""

from __future__ import annotations

from pathlib import Path

import mainframe_tools
import polars as pl

from file_validator.utils import get_total_length, scan_parquet_output


def main(input_path: str, output_path: str, schema: dict) -> pl.LazyFrame:
    out = Path(output_path)
    if not out.exists():
        mainframe_tools.parse_and_write_parquet(
            str(input_path),
            str(out),
            schema,
            get_total_length(schema, line_terminated=True),
            500_000,
        )
    return scan_parquet_output(out)
