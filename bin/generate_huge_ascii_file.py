#!/usr/bin/env python3
"""Generate a huge ASCII file with fixed-size records.

Record layout (fixed-width, ASCII):
- FULL_NAME: PIC A(50)
- YEAR:      PIC 9(4)
- AMOUNT:    PIC 9(9)V99 (stored as 11 digits, implied decimal)

Each record is 66 bytes including newline:
50 + 4 + 11 + 1
"""

from __future__ import annotations

import argparse
import random
import string
from pathlib import Path


DEFAULT_TARGET_BYTES = 2 * 1024**3  # 2 GiB
RECORD_SIZE_BYTES = 66


def random_full_name(rng: random.Random) -> str:
    """Build a random uppercase ASCII full name and pad to 50 chars."""
    first_len = rng.randint(3, 12)
    last_len = rng.randint(3, 16)
    first = "".join(rng.choices(string.ascii_uppercase, k=first_len))
    last = "".join(rng.choices(string.ascii_uppercase, k=last_len))
    full_name = f"{first} {last}"
    return full_name.ljust(50)[:50]


def random_year(rng: random.Random) -> str:
    return f"{rng.randint(1900, 2099):04d}"


def random_amount_implied_decimal(rng: random.Random) -> str:
    # PIC 9(9)V99 -> 11 digits, no explicit decimal separator.
    return f"{rng.randint(0, 99_999_999_999):011d}"


def build_record(rng: random.Random) -> bytes:
    line = (
        f"{random_full_name(rng)}"
        f"{random_year(rng)}"
        f"{random_amount_implied_decimal(rng)}\n"
    )
    return line.encode("ascii")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a huge fixed-size ASCII record file."
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path of generated file (e.g. data/huge_records.txt).",
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

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    bytes_written = 0
    batch_size = 10_000

    with args.output.open("wb") as out:
        while bytes_written < args.target_bytes:
            records = [build_record(rng) for _ in range(batch_size)]
            chunk = b"".join(records)
            out.write(chunk)
            bytes_written += len(chunk)

    print(
        f"Created {args.output} with {bytes_written} bytes "
        f"({bytes_written / 1024**3:.2f} GiB)."
    )
    print(f"Record size: {RECORD_SIZE_BYTES} bytes")


if __name__ == "__main__":
    main()
