"""Repo-relative paths for default data fixtures (benchmark, notebooks)."""

from __future__ import annotations

import os

from file_parser.utils.file_utils import repo_root

_DEFAULT_FILE_STEM = "huge_fixed_size_file"


def file_stem() -> str:
    return os.environ.get("MAINFRAME_FILE_STEM", _DEFAULT_FILE_STEM)


ROOT = repo_root()
DATA = ROOT / "data"

FILE_STEM = file_stem()

INPUT_PATH = DATA / f"{FILE_STEM}.dat"
INTERMEDIATE_OUTPUT_PATH = DATA / f"{FILE_STEM}.parquet"
OUTPUT_PATH = DATA / f"{FILE_STEM}_validations.parquet"
FORMULAS_PATH = ROOT / "formulas.txt"
