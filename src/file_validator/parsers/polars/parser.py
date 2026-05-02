"""Fixed-width file → Parquet (Polars only), no Rust extension.

Reads **line-delimited** records via :func:`polars.scan_csv` (one ``raw`` column),
parses fields with ``str.slice`` / ``strip_chars`` / ``cast`` in the Polars engine,
and writes a single Snappy Parquet file under the output folder.

For throughput on huge files, prefer ``file_validator.parsers.rust.file_parser``;
this path is simple and I/O- and engine-streaming-friendly, not multi-process.
"""

from __future__ import annotations

from pathlib import Path

from file_validator.types import FixedWidthSchema

from . import utils

# One Parquet file so :func:`file_validator.utils.scan_parquet_output` still matches
# ``shard_*.parquet`` in a directory.
_OUTPUT_NAME = "shard_0.parquet"


def parse_and_write_parquet(
    input_path: str,
    output_folder: str,
    schema_dict: FixedWidthSchema,
    record_size: int,
    rows_per_batch: int,
) -> None:
    """Parse a line-oriented fixed-width file and write Snappy Parquet.

    Same contract as ``mainframe_tools.parse_and_write_parquet``: ``schema_dict``
    values are ``(byte_offset, length)`` (implicit ``string``) or
    ``(byte_offset, length, type_string)``.

    The input must be **newline-separated** lines (e.g. ASCII + optional ``\\n`` after
    the payload, as in ``run.py`` with ``line_terminated=True``). Polars returns each
    line without the trailing newline; field offsets are still valid on the payload.

    ``record_size`` and ``rows_per_batch`` are kept for the :class:`MainframeParser`
    protocol; this implementation does not use them (parsing and sink are fully lazy).
    """
    _ = record_size, rows_per_batch
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)
    lf = utils.scan_fixed_width_lines_lazy(input_path, schema_dict)
    lf.sink_parquet(
        (out / _OUTPUT_NAME).as_posix(),
        compression="snappy",
    )
