"""Fixed-width file → Parquet (Polars / PyArrow), no Rust extension.

Parallelism uses one process per shard (like Rust/rayon). That keeps all CPUs busy,
but wall-clock time is still often **much slower** than the Rust extension because:

- Parsing still runs as **Python-level per-field work** (decode, ``int``, ``Decimal``,
  list appends) inside ``utils.write_shard``, whereas Rust uses tight loops over bytes
  with Arrow builders.
- Each batch builds Polars series from Python lists; Rust writes Arrow arrays directly.
- On **spawn** platforms (typical on macOS/Windows), worker processes pay a **cold
  import** cost for Polars/PyArrow each run; Linux **fork** inherits the parent's imports
  and is cheaper to start.

For fastest throughput on large files, use ``file_validator.parsers.rust.file_parser``.
"""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from file_validator.types import FixedWidthSchema

from . import utils


def parse_and_write_parquet(
    input_path: str,
    output_folder: str,
    schema_dict: FixedWidthSchema,
    record_size: int,
    rows_per_batch: int,
) -> None:
    """Parse a fixed-width binary file and write ``shard_{i}.parquet`` parts (Snappy).

    Same contract as ``mainframe_tools.parse_and_write_parquet``: ``schema_dict``
    values are ``(byte_offset, length)`` (implicit ``string``) or
    ``(byte_offset, length, type_string)``.

    Like the Rust extension, work is split across CPUs (one process per shard).
    Python threads would not parallelize the parsing loops here because those loops
    hold the GIL; ``ProcessPoolExecutor`` matches the Rust/rayon behavior instead.
    """
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)
    col_defs = utils.schema_from_dict(schema_dict)
    num_cores = utils.cpu_count()
    input_resolved = str(Path(input_path).resolve())
    total_records = Path(input_resolved).stat().st_size // record_size
    records_per_core = total_records // num_cores

    shard_jobs: list[tuple[int, int, Path]] = []
    for core_id in range(num_cores):
        start_rec = core_id * records_per_core
        if core_id == num_cores - 1:
            end_rec = total_records
        else:
            end_rec = (core_id + 1) * records_per_core
        shard_jobs.append((start_rec, end_rec, out / f"shard_{core_id}.parquet"))

    if num_cores <= 1:
        start_rec, end_rec, shard_path = shard_jobs[0]
        utils.write_shard_range(
            input_resolved,
            str(shard_path),
            col_defs,
            record_size,
            rows_per_batch,
            start_rec,
            end_rec,
        )
        return

    with ProcessPoolExecutor(max_workers=num_cores) as pool:
        futures = [
            pool.submit(
                utils.write_shard_range,
                input_resolved,
                str(shard_path),
                col_defs,
                record_size,
                rows_per_batch,
                start_rec,
                end_rec,
            )
            for start_rec, end_rec, shard_path in shard_jobs
        ]
        for fut in futures:
            fut.result()
