from __future__ import annotations

import time
from pathlib import Path
from typing import cast

import polars as pl
from file_parser.main import main
from file_parser.parsers.polars import file_parser
from file_parser.utils import get_schema_from_copybook, remove_file_or_tree
from formula_engine import compute_from_path

INPUT_PATH = "data/huge_fixed_size_file.dat"
INTERMEDIATE_OUTPUT_PATH = "data/huge_fixed_size_file.parquet"
OUTPUT_PATH = "data/huge_fixed_size_file_validations.parquet"
FORMULAS_PATH = Path(__file__).resolve().parent / "formulas.txt"

COPYBOOK = """
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
"""


def formulas_etl(
    df: pl.LazyFrame,
    formulas_path: Path = FORMULAS_PATH,
) -> pl.LazyFrame:
    """Apply validations and derived columns from a formulas file."""
    return cast(pl.LazyFrame, compute_from_path(formulas_path, df))


if __name__ == "__main__":
    print(f"Reading fixed-length file using {file_parser.__module__}")

    t0 = time.perf_counter()
    file_schema = get_schema_from_copybook(COPYBOOK)
    input_df = main(INPUT_PATH, INTERMEDIATE_OUTPUT_PATH, file_schema, file_parser)
    t1 = time.perf_counter()

    print(f"Stage 1 (Conversion to parquet) COMPLETED IN: {t1 - t0:.3f}s")

    result_lf = formulas_etl(input_df)
    result_lf.sink_parquet(OUTPUT_PATH)
    t2 = time.perf_counter()

    print(f"Stage 2 (Formulas: validations + derivatives) COMPLETED IN: {t2 - t1:.3f}s")
    print(f"Total: {t2 - t0:.3f}s")

    remove_file_or_tree(INTERMEDIATE_OUTPUT_PATH)
