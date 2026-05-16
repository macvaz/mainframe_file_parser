from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import cast

import polars as pl
import pytest
from formula_engine import FormulaSyntaxError, compute, parse_formulas
from formula_engine.graph.dag import create_dag, execution_order

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE_VALIDATIONS = FIXTURES / "sample_validations.formulas"
SAMPLE_DERIVATIVE = FIXTURES / "sample_derivative.formulas"


def test_polars_transformer_builds_indicator_columns() -> None:
    indicators = """
a: SUM({SUM_1}, {x})
b: PROD({a}, 2)
"""
    assignments = parse_formulas(indicators)
    dag = create_dag(assignments)
    lf = pl.LazyFrame({"SUM_1": [1.0, 2.0], "x": [3.0, 4.0]})
    for name, info in execution_order(dag, assignments):
        lf = lf.with_columns(info.expr.alias(name))

    out = cast(pl.DataFrame, lf.collect())
    assert out["a"].to_list() == [4.0, 6.0]
    assert out["b"].to_list() == [8.0, 12.0]


def test_sample_validation_formulas() -> None:
    lf = pl.LazyFrame(
        {
            "FULL_NAME": ["123456789", "1234567890"],
            "YEAR": [1950, 1899],
            "AMOUNT": [Decimal("100.00"), Decimal("999999999.99")],
        }
    )
    out = cast(pl.DataFrame, compute(SAMPLE_VALIDATIONS, lf).collect())

    assert out["VALID_NAME"].to_list() == [True, False]
    assert out["VALID_YEAR"].to_list() == [True, False]
    assert out["VALID_AMOUNT"].to_list() == [True, False]
    assert out["VALID_NAME_2"].to_list() == [False, True]
    assert out["VALID_YEAR_2"].to_list() == [True, False]
    assert out["VALID_AMOUNT_2"].to_list() == [True, False]


def test_sample_derivative_formulas() -> None:
    lf = pl.LazyFrame(
        {
            "YEAR": [1950, 1899],
            "AMOUNT": [Decimal("100.00"), Decimal("999999999.99")],
        }
    )
    out = cast(pl.DataFrame, compute(SAMPLE_DERIVATIVE, lf).collect())

    assert out["IND_AMOUNT_PLUS_YEAR"].to_list() == [
        Decimal("2050.00"),
        Decimal("1000001898.99"),
    ]
    assert out["IND_AMOUNT_PLUS_YEAR_DOUBLE"].to_list() == [
        4100.0,
        2_000_003_797.98,
    ]


def test_compute_from_inline_validation_formulas() -> None:
    formulas = "VALID_NAME: LEN({FULL_NAME}) == 9"
    lf = pl.LazyFrame({"FULL_NAME": ["abcdefghi", "abcdefghij"]})
    assignments = parse_formulas(formulas)
    dag = create_dag(assignments)
    for name, info in execution_order(dag, assignments):
        lf = lf.with_columns(info.expr.alias(name))
    out = cast(pl.DataFrame, lf.collect())
    assert out["VALID_NAME"].to_list() == [True, False]


@pytest.mark.parametrize(
    "formula",
    [
        "VALID_NAME: LEN(FULL_NAME) == 9",
        "VALID_YEAR: BETWEEN(YEAR, 1900, 2000)",
        "a: SUM(SUM_1, {x})",
        "VALID_NAME: {FULL_NAME} == NAME",
        "b: PROD(a, 2)",
    ],
)
def test_bare_column_or_indicator_reference_requires_braces(formula: str) -> None:
    with pytest.raises(FormulaSyntaxError, match="braces|Bare reference"):
        parse_formulas(formula)
