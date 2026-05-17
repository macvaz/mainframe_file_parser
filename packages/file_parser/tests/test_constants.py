from __future__ import annotations

import pytest

from file_parser.constants import file_stem


def test_file_stem_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MAINFRAME_FILE_STEM", raising=False)
    assert file_stem() == "huge_fixed_size_file"

    monkeypatch.setenv("MAINFRAME_FILE_STEM", "custom_stem")
    assert file_stem() == "custom_stem"
