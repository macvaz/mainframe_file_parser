"""Helpers for fixed-width → Parquet via Polars (line-oriented ``scan_csv`` + expressions)."""

from __future__ import annotations

from pathlib import Path

import polars as pl

from file_parser.types import ColumnDefinition, FileSchema


def _polars_dtype(col: ColumnDefinition) -> pl.DataType:
    if col.kind == "string":
        return pl.String()
    if col.kind == "integer":
        return pl.Int64()
    if col.kind == "float":
        return pl.Float64()
    assert col.kind == "decimal" and col.precision is not None and col.scale is not None
    return pl.Decimal(col.precision, col.scale)


def _column_expr(raw: str, col: ColumnDefinition) -> pl.Expr:
    """Slice fixed-width text fields and cast in Polars (Rust engine), no Python UDFs."""
    field = pl.col(raw).str.slice(col.start, col.length).str.strip_chars()
    if col.kind == "string":
        return field.alias(col.name)
    if col.kind == "decimal":
        assert col.precision is not None and col.scale is not None
        dtype = pl.Decimal(col.precision, col.scale)
        # COBOL implied decimal (PIC … V99): digits are unscaled; scale is metadata.
        unscaled = field.cast(pl.Int64, strict=False)
        scaled = unscaled if col.scale == 0 else unscaled / pl.lit(10**col.scale)
        return scaled.cast(dtype, strict=False).alias(col.name)
    return field.cast(_polars_dtype(col), strict=False).alias(col.name)


def column_exprs_from_schema(raw_column: str, schema: FileSchema) -> list[pl.Expr]:
    """Build ``with_columns`` expressions: fixed-width layout → typed columns."""
    return [_column_expr(raw_column, c) for c in schema]


def parse_file_according_to_schema(
    path: str | Path, schema: FileSchema
) -> pl.LazyFrame:
    """Lazy pipeline: file → rows, each physical line parsed per ``schema_dict``.

    Uses :func:`polars.scan_csv` with a single ``raw`` column (separator that does not
    appear in the data), then applies field slices and native ``cast`` expressions.
    Polars returns each line **without** the trailing newline; field ``(start, length)``
    offsets refer to the payload bytes.
    """
    lf = pl.scan_csv(
        str(Path(path).resolve()),
        has_header=False,
        new_columns=["raw"],
        separator="\x00",
        truncate_ragged_lines=True,
    )
    return lf.with_columns(column_exprs_from_schema("raw", schema)).drop("raw")
