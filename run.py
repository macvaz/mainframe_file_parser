from __future__ import annotations

import time

import polars as pl

from file_validator.main import main
from file_validator.parsers.polars import file_parser
from file_validator.utils import get_schema_from_copybook, remove_file_or_tree

INPUT_PATH = "data/huge_fixed_size_file.dat"
INTERMEDIATE_OUTPUT_PATH = "data/huge_fixed_size_file.parquet"
OUTPUT_PATH = "data/huge_fixed_size_file_validations.parquet"

COPYBOOK = """
       01  FILE-RECORD.
           05  FULL-NAME                  PIC X(50).
           05  YEAR                       PIC 9(4).
           05  AMOUNT                     PIC 9(09)V99.
"""


def validation_etl(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        VALID_NAME=pl.col("FULL_NAME").str.len_bytes() == 9,
        VALID_YEAR=pl.col("YEAR").is_between(1900, 2000),
        VALID_AMOUNT=pl.col("AMOUNT").is_between(0, 672581176.44),
        VALID_NAME_2=pl.col("FULL_NAME").str.len_bytes() == 10,
        VALID_YEAR_2=pl.col("YEAR").is_between(1900, 1950),
        VALID_AMOUNT_2=pl.col("AMOUNT").is_between(0, 2281176.44),
    )


if __name__ == "__main__":
    print(f"Reading fixed-length file using {file_parser.__module__}")

    t0 = time.perf_counter()
    file_schema = get_schema_from_copybook(COPYBOOK)
    input_df = main(INPUT_PATH, INTERMEDIATE_OUTPUT_PATH, file_schema, file_parser)
    t1 = time.perf_counter()

    print(f"Stage 1 (Conversion to parquet) COMPLETED IN: {t1 - t0:.3f}s")

    validations_lf = validation_etl(input_df)
    validations_lf.sink_parquet(OUTPUT_PATH)
    t2 = time.perf_counter()

    print(f"Stage 2 (Validation calculations) COMPLETED IN: {t2 - t1:.3f}s")
    print(f"Total: {t2 - t0:.3f}s")

    remove_file_or_tree(INTERMEDIATE_OUTPUT_PATH)
