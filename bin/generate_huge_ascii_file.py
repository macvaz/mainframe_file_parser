#!/usr/bin/env python3
"""Generate a huge line-oriented fixed-width ASCII file from a COBOL copybook.

Record layout and field widths are taken from the copybook (see
:func:`file_validator.utils.cobol.get_schema_from_copybook`). Data generation is
driven only by column **type** (``string``, ``integer``, ``decimal``), not by
field names. Each line is the fixed-width payload plus a single ``\\n`` (use
:func:`file_validator.utils.file_utils.get_total_length` with
``line_terminated=True`` for full record size).

Only these kinds are supported for random data: **string**, **integer**,
**decimal** (the copybook may use other PICs; anything that does not map to
these must be rejected for this tool).
"""

from __future__ import annotations

import argparse
import random
import string
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from file_validator.types import ColumnDefinition, FileSchema  # noqa: E402
from file_validator.utils.cobol import get_schema_from_copybook  # noqa: E402
from file_validator.utils.file_utils import get_total_length  # noqa: E402

DEFAULT_TARGET_BYTES = 2 * 1024**3  # 2 GiB

_ALLOWED_KINDS = frozenset({"string", "integer", "decimal"})


def validate_generator_schema(schema: FileSchema) -> None:
    """Ensure every column uses a kind this script can synthesize."""
    for col in schema:
        if col.kind not in _ALLOWED_KINDS:
            raise ValueError(
                f"copybook field {col.name!r} has kind {col.kind!r}; "
                "this generator only supports: string, integer, decimal"
            )
        if col.kind == "decimal" and (col.precision is None or col.scale is None):
            raise ValueError(
                f"decimal field {col.name!r} must have precision and scale set"
            )


def random_string_field(rng: random.Random, length: int) -> str:
    """Random uppercase ASCII letters and spaces, exactly ``length`` bytes."""
    if length <= 0:
        return ""
    alphabet = string.ascii_uppercase + " "
    return "".join(rng.choices(alphabet, k=length))


def random_integer_field(rng: random.Random, length: int) -> str:
    """Unsigned numeric string, exactly ``length`` digits (leading zeros allowed)."""
    if length <= 0:
        return ""
    upper = 10**length - 1
    return f"{rng.randint(0, upper):0{length}d}"


def random_decimal_field(rng: random.Random, col: ColumnDefinition) -> str:
    """Implied-decimal digits only (no separator), ``col.length`` characters."""
    p = col.precision
    s = col.scale
    assert p is not None and s is not None
    max_unscaled = 10**p - 1
    value = rng.randint(0, max_unscaled)
    return f"{value:0{col.length}d}"


def random_payload_slice(rng: random.Random, col: ColumnDefinition) -> str:
    """Dispatch by column **kind** (not name)."""
    if col.kind == "string":
        return random_string_field(rng, col.length)
    if col.kind == "integer":
        return random_integer_field(rng, col.length)
    if col.kind == "decimal":
        return random_decimal_field(rng, col)
    raise AssertionError(f"unhandled kind {col.kind!r}")


def build_record(rng: random.Random, schema: FileSchema) -> bytes:
    """One physical line: fixed-width payload (ASCII) then ``\\n``."""
    payload_len = get_total_length(schema, line_terminated=False)
    buf = bytearray(payload_len)
    for col in schema:
        text = random_payload_slice(rng, col)
        raw = text.encode("ascii")
        if len(raw) != col.length:
            raise ValueError(
                f"internal error: field {col.name!r} produced {len(raw)} bytes, "
                f"expected {col.length}"
            )
        buf[col.start : col.start + col.length] = raw
    return bytes(buf) + b"\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a huge fixed-width ASCII file. Layout comes from a COBOL copybook; "
            "random values depend only on column types (string / integer / decimal)."
        )
    )
    parser.add_argument(
        "copybook",
        type=Path,
        help="Path to the COBOL copybook (.cpy) defining field positions and PICs.",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path of generated file (e.g. data/huge_fixed_size_file.dat).",
    )
    parser.add_argument(
        "--target-bytes",
        type=int,
        default=DEFAULT_TARGET_BYTES,
        help="Minimum file size in bytes (default: 2 GiB).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.target_bytes < DEFAULT_TARGET_BYTES:
        raise ValueError("target-bytes must be at least 2 GiB.")

    schema = get_schema_from_copybook(args.copybook)
    validate_generator_schema(schema)

    record_bytes = get_total_length(schema, line_terminated=True)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    bytes_written = 0
    batch_size = 10_000

    with args.output.open("wb") as out:
        while bytes_written < args.target_bytes:
            records = [build_record(rng, schema) for _ in range(batch_size)]
            chunk = b"".join(records)
            out.write(chunk)
            bytes_written += len(chunk)

    print(
        f"Created {args.output} with {bytes_written} bytes "
        f"({bytes_written / 1024**3:.2f} GiB)."
    )
    print(f"Record size (payload + newline): {record_bytes} bytes")


if __name__ == "__main__":
    main()
