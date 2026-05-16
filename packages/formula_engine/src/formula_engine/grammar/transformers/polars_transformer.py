import operator
from collections.abc import Callable
from typing import List

import polars as pl
from lark import Transformer, v_args

from formula_engine.common.types import Assignment, IndicatorInfo
from formula_engine.exceptions import FormulaSyntaxError


@v_args(inline=True)
class PolarsTransformer(Transformer):
    @v_args(inline=False)
    def start(self, assignments: Assignment | list[Assignment]) -> List[Assignment]:
        if isinstance(assignments, list):
            return assignments
        return [assignments]

    def assignment(self, name, indicator_info: IndicatorInfo) -> Assignment:
        return (str(name), indicator_info)

    def or_op(self, left, right) -> IndicatorInfo:
        return _combine_bool("or", left, right)

    def and_op(self, left, right) -> IndicatorInfo:
        return _combine_bool("and", left, right)

    def eq(self, left, right) -> IndicatorInfo:
        return _compare(operator.eq, left, right)

    def ne(self, left, right) -> IndicatorInfo:
        return _compare(operator.ne, left, right)

    def lt(self, left, right) -> IndicatorInfo:
        return _compare(operator.lt, left, right)

    def le(self, left, right) -> IndicatorInfo:
        return _compare(operator.le, left, right)

    def gt(self, left, right) -> IndicatorInfo:
        return _compare(operator.gt, left, right)

    def ge(self, left, right) -> IndicatorInfo:
        return _compare(operator.ge, left, right)

    def add(self, left, right) -> IndicatorInfo:
        return _combine_numeric(operator.add, left, right)

    def sub(self, left, right) -> IndicatorInfo:
        return _combine_numeric(operator.sub, left, right)

    def mul(self, left, right) -> IndicatorInfo:
        return _combine_numeric(operator.mul, left, right)

    def div(self, left, right) -> IndicatorInfo:
        return _combine_numeric(operator.truediv, left, right)

    def function(self, name, *args) -> IndicatorInfo:
        infos = [_as_indicator_info(arg) for arg in args]
        name = str(name)
        if name == "SUM":
            return _fold_numeric(operator.add, infos)
        if name == "PROD":
            return _fold_numeric(operator.mul, infos)
        if name == "DIV":
            return _fold_numeric(operator.truediv, infos)
        if name == "LEN":
            if len(infos) != 1:
                msg = "LEN expects exactly one argument"
                raise ValueError(msg)
            info = infos[0]
            return IndicatorInfo(info.expr.str.len_bytes(), list(info.references))
        if name == "BETWEEN":
            if len(infos) != 3:
                msg = "BETWEEN expects exactly three arguments"
                raise ValueError(msg)
            value, low, high = infos
            expr = value.expr.is_between(low.expr, high.expr)
            refs = _merge_references(value, low, high)
            return IndicatorInfo(expr, refs)
        msg = f"unknown function {name!r}"
        raise ValueError(msg)

    def ref_body(self, *items: dict[str, object] | str) -> str | list[dict[str, object]]:
        if len(items) == 1 and isinstance(items[0], str):
            return items[0]
        return [item for item in items if isinstance(item, dict)]

    def reference(self, ref_body: str | list[dict[str, object]]) -> IndicatorInfo:
        if isinstance(ref_body, str):
            return IndicatorInfo(pl.col(ref_body), [ref_body])

        ref: dict[str, object] = {}
        for item in ref_body:
            ref.update(item)
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
        msg = (
            f"Bare reference '{value}' is not allowed; "
            f"use {{{value}}} for column or indicator references."
        )
        raise FormulaSyntaxError(msg)
    raise TypeError(f"expected IndicatorInfo, got {type(value)!r}")


def _merge_references(*infos: IndicatorInfo) -> list[str]:
    refs: list[str] = []
    for info in infos:
        refs.extend(info.references)
    return refs


def _compare(
    op: Callable[[pl.Expr, pl.Expr], pl.Expr],
    left: IndicatorInfo | str,
    right: IndicatorInfo | str,
) -> IndicatorInfo:
    l = _as_indicator_info(left)
    r = _as_indicator_info(right)
    return IndicatorInfo(op(l.expr, r.expr), _merge_references(l, r))


def _combine_bool(
    op: str,
    left: IndicatorInfo | str,
    right: IndicatorInfo | str,
) -> IndicatorInfo:
    l = _as_indicator_info(left)
    r = _as_indicator_info(right)
    if op == "or":
        expr = l.expr | r.expr
    else:
        expr = l.expr & r.expr
    return IndicatorInfo(expr, _merge_references(l, r))


def _combine_numeric(
    op: Callable[[pl.Expr, pl.Expr], pl.Expr],
    left: IndicatorInfo | str,
    right: IndicatorInfo | str,
) -> IndicatorInfo:
    l = _as_indicator_info(left)
    r = _as_indicator_info(right)
    return IndicatorInfo(op(l.expr, r.expr), _merge_references(l, r))


def _fold_numeric(
    op: Callable[[pl.Expr, pl.Expr], pl.Expr],
    infos: list[IndicatorInfo],
) -> IndicatorInfo:
    if not infos:
        msg = "numeric function requires at least one argument"
        raise ValueError(msg)
    result = infos[0]
    for next_info in infos[1:]:
        result = IndicatorInfo(
            op(result.expr, next_info.expr),
            _merge_references(result, next_info),
        )
    return result
