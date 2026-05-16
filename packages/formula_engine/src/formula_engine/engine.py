from __future__ import annotations

from pathlib import Path

import polars as pl
from lark.exceptions import LarkError

from formula_engine.common.types import Assignment
from formula_engine.exceptions import FormulaSyntaxError
from formula_engine.grammar.grammar import parser
from formula_engine.grammar.transformers.polars_transformer import PolarsTransformer
from formula_engine.graph.dag import create_dag, execution_order


def parse_formulas(source: str) -> list[Assignment]:
    """Parse formula text into named Polars expression assignments."""
    try:
        tree = parser.parse(source)
    except LarkError as exc:
        msg = (
            f"Invalid formula syntax: {exc}. "
            "Column and indicator references must use braces, e.g. {FULL_NAME}."
        )
        raise FormulaSyntaxError(msg) from exc
    result = PolarsTransformer().transform(tree)
    if isinstance(result, list):
        return result
    return [result]


def load_formulas(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")


def compute(
    formulas: str,
    datapoints_df: pl.DataFrame | pl.LazyFrame,
) -> pl.DataFrame | pl.LazyFrame:
    """Evaluate formulas and append each result as a new column."""
    assignments = parse_formulas(formulas)
    dag = create_dag(assignments)
    for indicator_name, indicator_info in execution_order(dag, assignments):
        datapoints_df = datapoints_df.with_columns(
            indicator_info.expr.alias(indicator_name)
        )
    return datapoints_df


def compute_from_path(
    path: str | Path,
    datapoints_df: pl.DataFrame | pl.LazyFrame,
) -> pl.DataFrame | pl.LazyFrame:
    """Load formulas from a file and evaluate them on ``datapoints_df``."""
    return compute(load_formulas(path), datapoints_df)
