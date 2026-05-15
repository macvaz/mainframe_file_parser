from typing import List

import polars as pl

from formula_engine.common.types import Assignment
from formula_engine.grammar.grammar import parser
from formula_engine.grammar.transformers.polars_transformer import PolarsTransformer
from formula_engine.graph.dag import create_dag, iterate_by_generation


def _preview(df: pl.DataFrame | pl.LazyFrame) -> None:
    if isinstance(df, pl.LazyFrame):
        print(df.head().collect())
    else:
        print(df.head())


def compute(
    indicators: str,
    datapoints_df: pl.DataFrame | pl.LazyFrame,
) -> pl.DataFrame | pl.LazyFrame:
    tree = parser.parse(indicators)
    print(tree.pretty())

    transformer = PolarsTransformer()
    assignments: List[Assignment] = transformer.transform(tree)

    import pprint

    pprint.pprint(assignments)

    _preview(datapoints_df)

    dag = create_dag(assignments)

    print("Nodes: ", dag.nodes())
    print("Edges: ", dag.edges())

    iterate_by_generation(dag)

    for indicator_name, indicator_info in assignments:
        datapoints_df = datapoints_df.with_columns(
            indicator_info.expr.alias(indicator_name)
        )

    _preview(datapoints_df)
    return datapoints_df
