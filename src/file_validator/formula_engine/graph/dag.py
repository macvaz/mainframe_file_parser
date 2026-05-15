from typing import List
import rustworkx as rx

from file_validator.formula_engine.common.types import Assignment


def create_dag(formulas: List[Assignment]):
    dag = rx.PyDiGraph()

    node_map = {}

    # Adding nodes
    for indicator_name, _ in formulas:
        node_map[indicator_name] = dag.add_node(indicator_name)

    # Adding edges
    for indicator_name, indicator_info in formulas:
        source_node = node_map[indicator_name]
        for target_name in indicator_info.references:
            if target_name in node_map:
                target_node = node_map[target_name]
                dag.add_edge(
                    source_node, target_node, f"{indicator_name} -> {target_name}"
                )

    return dag


def iterate_by_generation(dag):
    generations = rx.topological_generations(dag)

    print("--- Execution Plan ---")
    for i, gen in enumerate(generations):
        node_names = [dag[idx] for idx in gen]
        print(f"Generation {i}: {node_names}")
