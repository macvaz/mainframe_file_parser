import operator
from typing import List

import polars as pl
from lark import Transformer, v_args

from formula_engine.common.types import Assignment, IndicatorInfo


@v_args(inline=True)
class PolarsTransformer(Transformer):
    def start(self, *assignments) -> List[Assignment]:
        return list(assignments)

    def assignment(self, name, indicator_info: IndicatorInfo) -> Assignment:
        return (str(name), indicator_info)

    def function(self, name, *args) -> IndicatorInfo:
        infos = [_as_indicator_info(arg) for arg in args]
        name = str(name)
        if name == "SUM":
            return _handle_binary_operator(operator.add, *infos)
        if name == "PROD":
            return _handle_binary_operator(operator.mul, *infos)
        if name == "DIV":
            return _handle_binary_operator(operator.truediv, *infos)
        return infos[0]

    def reference(self, *items) -> IndicatorInfo:
        ref = {}
        for i in items:
            if isinstance(i, dict):
                ref.update(i)
            else:
                col_name = str(i)
                return IndicatorInfo(pl.col(col_name), [col_name])

        col_name = f"{ref['table']}_R{ref['row']}_C{ref['column']}"
        return IndicatorInfo(pl.col(col_name), [col_name])

    def table(self, t) -> dict:
        return {"table": str(t).strip('"')}

    def row(self, r) -> dict:
        return {"row": int(r)}

    def column(self, c) -> dict:
        return {"column": int(c)}

    def identifier(self, id) -> str:
        return str(id)

    def NUMBER(self, n) -> IndicatorInfo:
        return IndicatorInfo(pl.lit(float(n)), [])


def _as_indicator_info(value: IndicatorInfo | str) -> IndicatorInfo:
    if isinstance(value, IndicatorInfo):
        return value
    if isinstance(value, str):
        return IndicatorInfo(pl.col(value), [value])
    raise TypeError(f"expected IndicatorInfo or column name, got {type(value)!r}")


def _handle_binary_operator(op_function: operator, *infos: IndicatorInfo) -> IndicatorInfo:
    result_expr = infos[0].expr
    result_ref = list(infos[0].references)
    for next_info in infos[1:]:
        result_expr = op_function(result_expr, next_info.expr)
        result_ref.extend(next_info.references)
    return IndicatorInfo(result_expr, result_ref)
