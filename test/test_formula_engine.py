from __future__ import annotations

import polars as pl

from file_validator.formula_engine.grammar.grammar import parser
from file_validator.formula_engine.grammar.transformers.polars_transformer import (
    PolarsTransformer,
)


def test_polars_transformer_builds_indicator_columns() -> None:
    indicators = """
a: SUM({SUM_1}, x)
b: PROD({a}, 2)
"""
    assignments = PolarsTransformer().transform(parser.parse(indicators))
    lf = pl.LazyFrame({"SUM_1": [1.0, 2.0], "x": [3.0, 4.0]})
    for name, info in assignments:
        lf = lf.with_columns(info.expr.alias(name))

    out = lf.collect()
    assert out["a"].to_list() == [4.0, 6.0]
    assert out["b"].to_list() == [8.0, 12.0]
