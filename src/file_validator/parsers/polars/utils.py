"""Helpers for fixed-width parsing and sharded Parquet output."""

from __future__ import annotations

import mmap
import os
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import polars as pl
import pyarrow.parquet as pq

from file_validator.types import FixedWidthSchema


@dataclass(frozen=True)
class _ColDef:
    name: str
    start: int
    length: int
    kind: str  # string | integer | float | decimal
    precision: int | None = None
    scale: int | None = None


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


def schema_from_dict(schema_dict: FixedWidthSchema) -> list[_ColDef]:
    cols: list[_ColDef] = []
    for name, pos in schema_dict.items():
        if isinstance(pos, tuple) and len(pos) == 3:
            start, ln, t = pos
            kind, prec, sc = _type_from_str(str(t))
            cols.append(
                _ColDef(
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
            cols.append(_ColDef(str(name), int(start), int(ln), "string", None, None))
        else:
            raise TypeError("schema values must be (start, len) or (start, len, type)")
    return cols


def _polars_dtype(col: _ColDef) -> pl.DataType:
    if col.kind == "string":
        return pl.String
    if col.kind == "integer":
        return pl.Int64
    if col.kind == "float":
        return pl.Float64
    assert col.kind == "decimal" and col.precision is not None and col.scale is not None
    return pl.Decimal(col.precision, col.scale)


def _parse_string(val: bytes | memoryview) -> str:
    b = val.tobytes() if isinstance(val, memoryview) else val
    return b.decode("utf-8", errors="replace").strip()


def _parse_int(name: str, val: bytes | memoryview) -> int | None:
    b = val.tobytes() if isinstance(val, memoryview) else val
    s = b.decode("utf-8", errors="replace").strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError as e:
        raise ValueError(
            f"failed parsing integer column {name!r} value {s!r}: {e}"
        ) from e


def _parse_float(name: str, val: bytes | memoryview) -> float | None:
    b = val.tobytes() if isinstance(val, memoryview) else val
    s = b.decode("utf-8", errors="replace").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError as e:
        raise ValueError(
            f"failed parsing float column {name!r} value {s!r}: {e}"
        ) from e


def _parse_decimal(
    name: str, val: bytes | memoryview, precision: int, scale: int
) -> Decimal | None:
    b = val.tobytes() if isinstance(val, memoryview) else val
    s = b.decode("utf-8", errors="replace").strip()
    if not s:
        return None
    if not s.isascii() or not all(c.isdigit() for c in s):
        raise ValueError(f"decimal column {name!r} expected ASCII digits, got {s!r}")
    try:
        unscaled = int(s)
    except ValueError as e:
        raise ValueError(
            f"failed parsing decimal column {name!r} value {s!r}: {e}"
        ) from e
    base = 10**precision
    max_abs = base - 1
    if abs(unscaled) > max_abs:
        raise ValueError(
            f"decimal column {name!r} value unscaled={unscaled} exceeds "
            f"DECIMAL({precision},{scale}) (|max| = {max_abs})"
        )
    return Decimal(unscaled) / (Decimal(10) ** scale)


def _cell(col: _ColDef, slab: bytes | memoryview) -> Any:
    if col.kind == "string":
        return _parse_string(slab)
    if col.kind == "integer":
        return _parse_int(col.name, slab)
    if col.kind == "float":
        return _parse_float(col.name, slab)
    return _parse_decimal(col.name, slab, col.precision or 0, col.scale or 0)


def write_shard(
    mm: mmap.mmap,
    *,
    path: Path,
    col_defs: list[_ColDef],
    record_size: int,
    rows_per_batch: int,
    start_rec: int,
    end_rec: int,
) -> None:
    start_byte = start_rec * record_size
    n_rows = end_rec - start_rec

    if n_rows == 0:
        empty = pl.DataFrame(
            {c.name: pl.Series(c.name, [], dtype=_polars_dtype(c)) for c in col_defs}
        )
        empty.write_parquet(path, compression="snappy")
        return

    writer: pq.ParquetWriter | None = None
    row = 0
    try:
        while row < n_rows:
            batch_n = min(rows_per_batch, n_rows - row)
            cols_data: dict[str, list[Any]] = {c.name: [] for c in col_defs}
            for _ in range(batch_n):
                abs_start = start_byte + row * record_size
                rec = mm[abs_start : abs_start + record_size]
                row += 1
                for c in col_defs:
                    slab = rec[c.start : c.start + c.length]
                    cols_data[c.name].append(_cell(c, slab))
            df = pl.DataFrame(
                {
                    c.name: pl.Series(c.name, cols_data[c.name], dtype=_polars_dtype(c))
                    for c in col_defs
                }
            )
            table = df.to_arrow()
            if writer is None:
                writer = pq.ParquetWriter(
                    path.as_posix(), table.schema, compression="snappy"
                )
            writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()


def write_shard_range(
    input_path: str,
    output_shard_path: str,
    col_defs: list[_ColDef],
    record_size: int,
    rows_per_batch: int,
    start_rec: int,
    end_rec: int,
) -> None:
    """Memory-map ``input_path`` and write a single shard file (for worker processes)."""
    with open(input_path, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            write_shard(
                mm,
                path=Path(output_shard_path),
                col_defs=col_defs,
                record_size=record_size,
                rows_per_batch=rows_per_batch,
                start_rec=start_rec,
                end_rec=end_rec,
            )
        finally:
            mm.close()


def cpu_count() -> int:
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1
