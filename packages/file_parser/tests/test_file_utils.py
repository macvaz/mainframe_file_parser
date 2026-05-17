from __future__ import annotations

from pathlib import Path
from typing import cast

import polars as pl
import pytest

from file_parser.types import ColumnDefinition
from file_parser.utils.file_utils import (
    PARQUET_OUTPUT_FILENAME,
    get_total_length,
    remove_file_or_tree,
    repo_root,
    scan_parquet_output,
)

_SCHEMA: list[ColumnDefinition] = [
    ColumnDefinition("A", 0, 2, "string", None, None),
    ColumnDefinition("B", 2, 3, "integer", None, None),
]


def test_get_total_length_plain_and_line_terminated() -> None:
    assert get_total_length(_SCHEMA) == 5
    assert get_total_length(_SCHEMA, line_terminated=True) == 6


def test_get_total_length_rejects_negative_offsets() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        get_total_length([ColumnDefinition("X", -1, 2, "string", None, None)])
    with pytest.raises(ValueError, match="non-negative"):
        get_total_length([ColumnDefinition("X", 0, -1, "string", None, None)])


def test_scan_parquet_output_single_file(tmp_path: Path) -> None:
    path = tmp_path / "one.parquet"
    pl.DataFrame({"x": [1]}).write_parquet(path)
    out = cast(pl.DataFrame, scan_parquet_output(path).collect())
    assert out["x"].to_list() == [1]


def test_scan_parquet_output_directory_data_parquet(tmp_path: Path) -> None:
    out_dir = tmp_path / "polars_out"
    out_dir.mkdir()
    pl.DataFrame({"y": [2]}).write_parquet(out_dir / PARQUET_OUTPUT_FILENAME)
    out = cast(pl.DataFrame, scan_parquet_output(out_dir).collect())
    assert out["y"].to_list() == [2]


def test_scan_parquet_output_directory_shard_glob(tmp_path: Path) -> None:
    out_dir = tmp_path / "rust_out"
    out_dir.mkdir()
    pl.DataFrame({"z": [3]}).write_parquet(out_dir / "shard_0.parquet")
    out = cast(pl.DataFrame, scan_parquet_output(out_dir).collect())
    assert out["z"].to_list() == [3]


def test_scan_parquet_output_empty_directory_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError, match="No Parquet output"):
        scan_parquet_output(empty)


def test_remove_file_or_tree_file_and_directory(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    remove_file_or_tree(f)
    assert not f.exists()

    d = tmp_path / "d"
    d.mkdir()
    (d / "inner.txt").write_text("y", encoding="utf-8")
    remove_file_or_tree(d)
    assert not d.exists()


def test_remove_file_or_tree_missing_is_noop(tmp_path: Path) -> None:
    remove_file_or_tree(tmp_path / "does_not_exist")


def test_repo_root_finds_pyproject() -> None:
    root = repo_root()
    assert (root / "pyproject.toml").is_file()


def test_repo_root_raises_when_not_found(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError, match="pyproject.toml"):
        repo_root()
