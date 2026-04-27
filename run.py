from __future__ import annotations

import time

import polars as pl

from file_validator.main import main

INPUT_PATH = "data/huge_fixed_size_file.dat"
INTERMEDIATE_OUTPUT_PATH = "data/huge_fixed_size_file.parquet"
OUTPUT_PATH = "data/huge_fixed_size_file_validations.parquet"

SCHEMA = {
    "FULL_NAME": (0, 50, "string"),
    "YEAR": (50, 4, "integer"),
    "AMOUNT": (54, 11, "decimal(11,2)"),
}


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
    t0 = time.perf_counter()
    input_df = main(INPUT_PATH, INTERMEDIATE_OUTPUT_PATH, SCHEMA)
    t1 = time.perf_counter()
    validations_lf = validation_etl(input_df)
    validations_lf.sink_parquet(OUTPUT_PATH)
    t2 = time.perf_counter()

    print(f"Stage 1 ({INTERMEDIATE_OUTPUT_PATH}): {t1 - t0:.3f}s | ")
    print(f"Stage 2 (validations + {OUTPUT_PATH}): {t2 - t1:.3f}s | ")
    print(f"Total: {t2 - t0:.3f}s")
