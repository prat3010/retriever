"""Declarative Workflow Compiler & Kahn's Cycle-Detecting Topological Sorter (M126).

Compiles visually designed DAG graphs into strict execution graphs with:
- Kahn's algorithm for linear topological sorting and cycle detection.
- Level-based parallel stage partitioning (for concurrent sub-branch execution).
- Variable contract verification between antecedent outputs and descendant inputs.
- Zero external framework or database imports (pure domain service).
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque

from src.domain.abstractions.workflow_dag import (
    DAGCompilerResult,
    DAGNodeType,
    WorkflowDAGGraph,
)

logger = logging.getLogger(__name__)


class CyclicWorkflowError(ValueError):
    """Raised when a directed cycle is detected in the workflow graph."""

    pass


class InvalidWorkflowGraphError(ValueError):
    """Raised when the workflow graph contains structural errors or undefined node references."""

    pass


class DAGWorkflowCompiler:
    """Pure domain compiler for declarative workflow DAG validation and staging."""

    def compile(
        self, graph: WorkflowDAGGraph, raise_on_error: bool = True
    ) -> DAGCompilerResult:
        """Validate, check cycles, and partition the DAG into parallel execution stages.

        Args:
            graph: The declarative workflow graph to compile.
            raise_on_error: If True, raises exceptions on validation failure or cycles.
                            If False, populates `errors` in `DAGCompilerResult`.

        Returns:
            DAGCompilerResult containing topological order, parallel stages, and variable map.
        """
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Structural Node Validation
        if not graph.nodes:
            err = "Workflow graph must contain at least one node."
            if raise_on_error:
                raise InvalidWorkflowGraphError(err)
            return DAGCompilerResult(graph_id=graph.id, is_valid=False, errors=[err])

        node_map = {n.id: n for n in graph.nodes}
        if len(node_map) != len(graph.nodes):
            err = "Duplicate node IDs detected in workflow graph."
            if raise_on_error:
                raise InvalidWorkflowGraphError(err)
            errors.append(err)

        has_input = any(n.type == DAGNodeType.INPUT for n in graph.nodes)
        has_output = any(n.type == DAGNodeType.OUTPUT for n in graph.nodes)
        if not has_input:
            warnings.append(
                "Graph does not specify an explicit INPUT node; initial trigger payload will default to global scope."
            )
        if not has_output:
            warnings.append(
                "Graph does not specify an explicit OUTPUT node; execution will return all step outputs."
            )

        # 2. Structural Edge Validation
        adjacency: dict[str, list[str]] = defaultdict(list)
        reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        in_degrees: dict[str, int] = {node.id: 0 for node in graph.nodes}

        for edge in graph.edges:
            if edge.source not in node_map:
                err = f"Edge '{edge.id}' references non-existent source node '{edge.source}'."
                errors.append(err)
                continue
            if edge.target not in node_map:
                err = f"Edge '{edge.id}' references non-existent target node '{edge.target}'."
                errors.append(err)
                continue
            if edge.source == edge.target:
                err = f"Self-loop detected on node '{edge.source}' in edge '{edge.id}'."
                errors.append(err)
                continue

            adjacency[edge.source].append(edge.target)
            reverse_adjacency[edge.target].append(edge.source)
            in_degrees[edge.target] += 1

        if errors:
            if raise_on_error:
                raise InvalidWorkflowGraphError("; ".join(errors))
            return DAGCompilerResult(
                graph_id=graph.id,
                is_valid=False,
                errors=errors,
                warnings=warnings,
            )

        # 3. Kahn's Topological Sort & Cycle Detection
        queue = deque([n_id for n_id, deg in in_degrees.items() if deg == 0])
        topological_order: list[str] = []
        in_degree_copy = in_degrees.copy()

        while queue:
            current = queue.popleft()
            topological_order.append(current)
            for neighbor in adjacency[current]:
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)

        # If topological sort does not include all nodes, a cycle exists
        if len(topological_order) < len(graph.nodes):
            cyclic_nodes = [n.id for n in graph.nodes if n.id not in topological_order]
            err = (
                f"Cyclic dependency detected in workflow DAG! "
                f"Nodes involved in cycle: {cyclic_nodes}"
            )
            if raise_on_error:
                raise CyclicWorkflowError(err)
            errors.append(err)
            return DAGCompilerResult(
                graph_id=graph.id,
                is_valid=False,
                errors=errors,
                warnings=warnings,
            )

        # 4. Level-Based Parallel Stage Partitioning
        # Compute maximum distance from any root node to each node
        node_levels: dict[str, int] = {}
        for node_id in topological_order:
            parents = reverse_adjacency[node_id]
            if not parents:
                node_levels[node_id] = 0
            else:
                node_levels[node_id] = max(node_levels[p] for p in parents) + 1

        max_level = max(node_levels.values()) if node_levels else 0
        stages_by_level: dict[int, list[str]] = defaultdict(list)
        for node_id, lvl in node_levels.items():
            stages_by_level[lvl].append(node_id)

        parallel_stages: list[list[str]] = [
            stages_by_level[lvl] for lvl in range(max_level + 1)
        ]

        # 5. Variable Binding Verification
        available_variables: set[str] = set()
        variable_bindings: dict[str, list[str]] = {}

        # If there's an input node, its output keys start the available scope
        for node_id in topological_order:
            node = node_map[node_id]
            # Check if required input_keys are supplied by upstream or root input
            missing_inputs = [
                var
                for var in node.input_keys
                if var not in available_variables and var != "query" and var != "context"
            ]
            if missing_inputs:
                warnings.append(
                    f"Node '{node.id}' ({node.title}) requires input keys {missing_inputs} "
                    f"which may not be produced by upstream nodes."
                )

            # Record what inputs this node consumes
            variable_bindings[node_id] = node.input_keys.copy()

            # Add this node's output keys to scope for downstream consumers
            available_variables.update(node.output_keys)
            # Default implicit outputs per node type
            if node.type == DAGNodeType.INPUT:
                available_variables.add("query")
            elif node.type == DAGNodeType.RETRIEVAL:
                available_variables.add("context")
                available_variables.add("retrieved_chunks")
            elif node.type == DAGNodeType.LLM:
                available_variables.add("response")
                available_variables.add("answer")

        return DAGCompilerResult(
            graph_id=graph.id,
            is_valid=True,
            topological_order=topological_order,
            parallel_stages=parallel_stages,
            variable_bindings=variable_bindings,
            warnings=warnings,
            errors=[],
        )
