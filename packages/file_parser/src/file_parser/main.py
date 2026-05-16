"""Convert fixed-width input to Parquet and scan results with Polars."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from file_parser.types import FileSchema, MainframeParser
from file_parser.utils import get_total_length, scan_parquet_output


def parse(
    input_path: str,
    output_path: str,
    schema: FileSchema,
    parser: MainframeParser,
) -> pl.LazyFrame:
    out = Path(output_path)
    if not out.exists():
        parser(
            str(input_path),
            str(out),
            schema,
            get_total_length(schema, line_terminated=True),
            500_000,
        )
    return scan_parquet_output(out)
