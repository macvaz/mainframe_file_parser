from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-huge",
        action="store_true",
        default=False,
        help="Include @pytest.mark.huge tests (multi-GB fixture; slow, needs disk).",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if config.getoption("--run-huge"):
        return
    deselected: list[pytest.Item] = []
    kept: list[pytest.Item] = []
    for item in items:
        if item.get_closest_marker("huge"):
            deselected.append(item)
        else:
            kept.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept
