from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from formula_engine import FormulaSyntaxError, parse_formulas
from formula_engine.engine import parse_formulas as engine_parse_formulas
from formula_engine.common.types import IndicatorInfo
from formula_engine.grammar.transformers import polars_transformer as pt


def _eval_formulas(source: str, columns: dict[str, list[object]]) -> pl.DataFrame:
    lf = pl.LazyFrame(columns)
    for name, info in parse_formulas(source):
        lf = lf.with_columns(info.expr.alias(name))
    return cast(pl.DataFrame, lf.collect())


def test_comparison_and_logical_operators() -> None:
    out = _eval_formulas(
        """
eq_v: {a} == {b}
ne_v: {a} != {b}
lt_v: {a} < {b}
le_v: {a} <= {b}
gt_v: {a} > {b}
ge_v: {a} >= {b}
and_v: ({a} < {b}) AND ({a} > 0)
or_v: ({a} < {b}) OR ({a} > {b})
""",
        {"a": [1.0, 3.0], "b": [2.0, 2.0]},
    )
    assert out["eq_v"].to_list() == [False, False]
    assert out["ne_v"].to_list() == [True, True]
    assert out["lt_v"].to_list() == [True, False]
    assert out["le_v"].to_list() == [True, False]
    assert out["gt_v"].to_list() == [False, True]
    assert out["ge_v"].to_list() == [False, True]
    assert out["and_v"].to_list() == [True, False]
    assert out["or_v"].to_list() == [True, True]


def test_arithmetic_and_div_function() -> None:
    out = _eval_formulas(
        """
add_v: {x} + {y}
sub_v: {x} - {y}
mul_v: {x} * {y}
div_v: {x} / {y}
fold_div: DIV({x}, {y}, 2)
""",
        {"x": [10.0, 8.0], "y": [2.0, 4.0]},
    )
    assert out["add_v"].to_list() == [12.0, 12.0]
    assert out["sub_v"].to_list() == [8.0, 4.0]
    assert out["mul_v"].to_list() == [20.0, 32.0]
    assert out["div_v"].to_list() == [5.0, 2.0]
    assert out["fold_div"].to_list() == [2.5, 1.0]


def test_len_and_between_and_attribute_reference() -> None:
    out = _eval_formulas(
        """
len_v: LEN({name})
between_v: BETWEEN({score}, 1, 10)
cell: {T("tbl")R(1)C(2)}
""",
        {
            "name": ["abc", "abcd"],
            "score": [5.0, 11.0],
            "tbl_R1_C2": [1.0, 2.0],
        },
    )
    assert out["len_v"].to_list() == [3, 4]
    assert out["between_v"].to_list() == [True, False]
    assert out["cell"].to_list() == [1.0, 2.0]


def test_single_assignment_start_wrapper() -> None:
    assignments = parse_formulas("only: {x} + 1")
    assert len(assignments) == 1
    assert assignments[0][0] == "only"


def test_invalid_lark_syntax_raises() -> None:
    with pytest.raises(FormulaSyntaxError, match="Invalid formula syntax"):
        parse_formulas("not valid syntax : : :")


def test_unknown_function_raises() -> None:
    transformer = pt.PolarsTransformer()
    col = IndicatorInfo(pl.col("x"), ["x"])
    with pytest.raises(ValueError, match="unknown function"):
        transformer.function("NOPE", col)


def test_len_wrong_arity_raises() -> None:
    transformer = pt.PolarsTransformer()
    col = IndicatorInfo(pl.col("a"), ["a"])
    with pytest.raises(ValueError, match="LEN expects exactly one"):
        transformer.function("LEN", col, col)


def test_between_wrong_arity_raises() -> None:
    transformer = pt.PolarsTransformer()
    col = IndicatorInfo(pl.col("a"), ["a"])
    with pytest.raises(ValueError, match="BETWEEN expects exactly three"):
        transformer.function("BETWEEN", col, IndicatorInfo(pl.lit(1.0), []))


def test_fold_numeric_empty_raises() -> None:
    with pytest.raises(ValueError, match="at least one argument"):
        pt._fold_numeric(lambda a, b: a, [])


def test_as_indicator_info_type_error() -> None:
    with pytest.raises(TypeError, match="expected IndicatorInfo"):
        pt._as_indicator_info(cast(IndicatorInfo | str, 42))


def test_as_indicator_info_bare_reference_string() -> None:
    with pytest.raises(FormulaSyntaxError, match="Bare reference"):
        pt._as_indicator_info("FULL_NAME")


def test_engine_parse_formulas_wraps_non_list_result() -> None:
    assignment = ("x", IndicatorInfo(pl.lit(1.0), []))
    tree = MagicMock()
    with patch("formula_engine.engine.parser.parse", return_value=tree):
        with patch("formula_engine.engine.PolarsTransformer") as transformer_cls:
            transformer_cls.return_value.transform.return_value = assignment
            result = engine_parse_formulas("x: 1")
    assert result == [assignment]


def test_polars_transformer_start_list_branch() -> None:
    transformer = pt.PolarsTransformer()
    a = ("x", IndicatorInfo(pl.lit(1.0), []))
    b = ("y", IndicatorInfo(pl.lit(2.0), []))
    assert transformer.start([a, b]) == [a, b]


def test_polars_transformer_start_single_assignment() -> None:
    transformer = pt.PolarsTransformer()
    assignment = ("x", IndicatorInfo(pl.lit(1.0), []))
    assert transformer.start(assignment) == [assignment]


def test_polars_transformer_ref_body_single_identifier() -> None:
    transformer = pt.PolarsTransformer()
    assert transformer.ref_body("FULL_NAME") == "FULL_NAME"
