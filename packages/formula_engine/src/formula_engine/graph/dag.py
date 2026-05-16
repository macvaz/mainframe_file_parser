from __future__ import annotations

import rustworkx as rx

from formula_engine.common.types import Assignment


def create_dag(formulas: list[Assignment]) -> rx.PyDiGraph:
    dag = rx.PyDiGraph()
    node_map: dict[str, int] = {}

    for indicator_name, _ in formulas:
        node_map[indicator_name] = dag.add_node(indicator_name)

    for indicator_name, indicator_info in formulas:
        indicator_node = node_map[indicator_name]
        for ref_name in indicator_info.references:
            if ref_name in node_map:
                ref_node = node_map[ref_name]
                dag.add_edge(
                    ref_node, indicator_node, f"{ref_name} -> {indicator_name}"
                )

    return dag


def execution_order(dag: rx.PyDiGraph, formulas: list[Assignment]) -> list[Assignment]:
    """Return assignments in dependency order (dependencies before dependents)."""
    by_name = {name: (name, info) for name, info in formulas}
    ordered: list[Assignment] = []
    for generation in rx.topological_generations(dag):
        for node_idx in generation:
            ordered.append(by_name[dag[node_idx]])
    return ordered
