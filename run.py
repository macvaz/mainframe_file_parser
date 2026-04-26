from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl

from file_validator.main import main

INPUT_PATH = "data/huge_fixed_size_file.dat"
SCHEMA = {
    "FULL_NAME": (0, 50, "string"),
    "YEAR": (50, 4, "integer"),
    "AMOUNT": (54, 11, "decimal(11,2)"),
}


def validation_etl(df: pl.LazyFrame) -> pl.LazyFrame:
    return df.with_columns(
        VALID_NAME=pl.col("FULL_NAME").str.len_bytes() == 8,
        VALID_YEAR=pl.col("YEAR").is_between(1900, 2000),
        VALID_AMOUNT=pl.col("AMOUNT").is_between(0, 672581176.44),
    )


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="file_validator_parquet_") as tmpdir:
        output_path = Path(tmpdir) / "parquet"
        input_df = main(INPUT_PATH, str(output_path), SCHEMA)
        validations_df = validation_etl(input_df)
        print(validations_df.head(10).collect())
