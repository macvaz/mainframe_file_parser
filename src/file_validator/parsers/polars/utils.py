"""Helpers for fixed-width → Parquet via Polars (line-oriented ``scan_csv`` + expressions)."""

from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from file_validator.types import ColumnDefinition, FileSchema

_DECIMAL_RE = re.compile(r"^decimal\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)\s*$", re.IGNORECASE)


def _type_from_str(raw: str) -> tuple[str, int | None, int | None]:
    lower = raw.strip().lower()
    m = _DECIMAL_RE.match(lower)
    if m is not None:
        p, s = int(m.group(1)), int(m.group(2))
        if p == 0 or p > 38:
            raise ValueError(f"decimal precision must be 1..=38, got {p} in {raw!r}")
        if s < 0 or s > p:
            raise ValueError(
                f"decimal scale must be 0..=precision, got scale={s} precision={p} in {raw!r}"
            )
        return "decimal", p, s
    match lower:
        case "string" | "str" | "text" | "utf8":
            return "string", None, None
        case "integer" | "int" | "int64":
            return "integer", None, None
        case "float" | "double" | "float64":
            return "float", None, None
        case other:
            raise ValueError(
                f"unsupported type {other!r}, expected one of: "
                "string|integer|float|decimal(p,s)"
            )


def _polars_dtype(col: ColumnDefinition) -> pl.DataType:
    if col.kind == "string":
        return pl.String()
    if col.kind == "integer":
        return pl.Int64()
    if col.kind == "float":
        return pl.Float64()
    assert col.kind == "decimal" and col.precision is not None and col.scale is not None
    return pl.Decimal(col.precision, col.scale)


def _field_expr(raw: str, col: ColumnDefinition) -> pl.Expr:
    """Slice fixed-width text fields and cast in Polars (Rust engine), no Python UDFs."""
    field = pl.col(raw).str.slice(col.start, col.length).str.strip_chars()
    if col.kind == "string":
        return field.alias(col.name)
    return field.cast(_polars_dtype(col), strict=False).alias(col.name)


def column_exprs_from_col_defs(
    raw_column: str, col_defs: list[ColumnDefinition]
) -> list[pl.Expr]:
    """Build ``with_columns`` expressions: fixed-width layout → typed columns."""
    return [_field_expr(raw_column, c) for c in col_defs]


def get_column_definitions_from_schema(
    schema_dict: FileSchema,
) -> list[ColumnDefinition]:
    cols: list[ColumnDefinition] = []
    for name, pos in schema_dict.items():
        if isinstance(pos, tuple) and len(pos) == 3:
            start, ln, t = pos
            kind, prec, sc = _type_from_str(str(t))
            cols.append(
                ColumnDefinition(
                    str(name),
                    int(start),
                    int(ln),
                    kind,
                    precision=prec,
                    scale=sc,
                )
            )
        elif isinstance(pos, tuple) and len(pos) == 2:
            start, ln = pos
            cols.append(
                ColumnDefinition(str(name), int(start), int(ln), "string", None, None)
            )
        else:
            raise TypeError("schema values must be (start, len) or (start, len, type)")
    return cols


def parse_file_according_to_schema(
    path: str | Path, schema_dict: FileSchema
) -> pl.LazyFrame:
    """Lazy pipeline: file → rows, each physical line parsed per ``schema_dict``.

    Uses :func:`polars.scan_csv` with a single ``raw`` column (separator that does not
    appear in the data), then applies field slices and native ``cast`` expressions.
    Polars returns each line **without** the trailing newline; field ``(start, length)``
    offsets refer to the payload bytes.
    """
    col_defs = get_column_definitions_from_schema(schema_dict)
    lf = pl.scan_csv(
        str(Path(path).resolve()),
        has_header=False,
        new_columns=["raw"],
        separator="\x00",
        truncate_ragged_lines=True,
    )
    return lf.with_columns(column_exprs_from_col_defs("raw", col_defs)).drop("raw")
