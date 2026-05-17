from __future__ import annotations

from pathlib import Path

from formula_engine.engine import load_formulas


def test_load_formulas_reads_file(tmp_path: Path) -> None:
    path = tmp_path / "rules.formulas"
    path.write_text("a: {x} + 1\n", encoding="utf-8")
    assert load_formulas(path) == "a: {x} + 1\n"
