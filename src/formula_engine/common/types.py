from dataclasses import dataclass
from typing import List

import polars as pl


@dataclass
class IndicatorInfo:
    expr: pl.Expr
    references: List[str]


type Assignment = tuple[str, IndicatorInfo]
