from __future__ import annotations


def test_run_huge_option_registered(pytestconfig) -> None:
    """Sanity check so `uv run pytest test/` is not an empty collection."""
    assert pytestconfig.getoption("--run-huge") in (True, False)
