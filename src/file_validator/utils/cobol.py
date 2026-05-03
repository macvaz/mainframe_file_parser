"""COBOL copybook → :class:`ColumnDefinition` list (fixed-width offsets)."""

from __future__ import annotations

from pathlib import Path

from python_cobol.python_cobol import (
    clean_cobol,
    clean_names,
    denormalize_cobol,
    parse_cobol,
)

from file_validator.types import ColumnDefinition, FileSchema


def _margin_lines(text: str) -> list[str]:
    """Prepare free-form copybook text for ``python_cobol`` (expects area A/B past column 6)."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.rstrip("\r\n")
        if not s.strip():
            continue
        if s.lstrip().startswith(("*", "/")):
            continue
        out.append(f"{' ' * 6}{s.strip()}\n")
    return out


def _pic_info_to_column(
    name: str, start: int, pic_info: dict[str, str | int]
) -> ColumnDefinition:
    raw_type = str(pic_info["type"])
    kind = raw_type.removeprefix("Signed ").strip()
    length = int(pic_info["length"])
    scale = int(pic_info["precision"])

    if kind == "Char":
        return ColumnDefinition(name, start, length, "string", None, None)
    if kind == "Integer":
        return ColumnDefinition(name, start, length, "integer", None, None)
    if kind == "Float":
        return ColumnDefinition(
            name,
            start,
            length,
            "decimal",
            precision=length,
            scale=scale,
        )
    msg = f"unsupported PIC classification {raw_type!r} for field {name!r}"
    raise ValueError(msg)


def get_schema_from_copybook(source: str | Path) -> FileSchema:
    """Parse a COBOL copybook and build sequential fixed-width column definitions.

    Uses ``python-cobol`` for PIC clauses. Elementary items with ``PIC`` are laid out
    in document order with ``start`` advancing by each field's byte ``length``.
    Group levels without ``PIC`` do not consume layout positions.

    Names use COBOL spelling with hyphens replaced by underscores (e.g. ``FULL-NAME``
    → ``FULL_NAME``).
    """
    text = (
        Path(source).read_text(encoding="utf-8") if isinstance(source, Path) else source
    )
    cleaned = clean_cobol(_margin_lines(text))
    rows = denormalize_cobol(parse_cobol(cleaned))
    clean_names(rows, True, False, True)

    cols: list[ColumnDefinition] = []
    offset = 0
    for row in rows:
        pic_info = row.get("pic_info")
        if pic_info is None:
            continue
        name = str(row["name"])
        cols.append(_pic_info_to_column(name, offset, pic_info))
        offset += int(pic_info["length"])

    if not cols:
        msg = "copybook has no elementary PIC clauses"
        raise ValueError(msg)
    return cols
