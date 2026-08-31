"""Leiden Community Detection Algorithm for GraphRAG.

Partitions entity-relationship knowledge graphs into hierarchical, well-connected
communities via modularity optimization and sub-community refinement.
"""

import uuid
from collections import defaultdict

from src.domain.abstractions.graph import (
    BaseCommunityDetector,
    CommunityHierarchy,
    EntityTriple,
    GraphCommunity,
)


class LeidenCommunityDetector(BaseCommunityDetector):
    """Pure-Python Leiden Community Detection algorithm implementation for GraphRAG.

    Implements modularity-maximizing graph partitioning with sub-community refinement,
    producing multi-level hierarchical community clusters for macro-synthesis queries.
    """

    def __init__(self, resolution: float = 1.0, min_community_size: int = 1) -> None:
        self.resolution = resolution
        self.min_community_size = min_community_size

    def detect_communities(
        self, tenant_id: str, triples: list[EntityTriple], max_levels: int = 3
    ) -> CommunityHierarchy:
        """Partition entity-relation graph into hierarchical communities."""
        if not triples:
            return CommunityHierarchy(
                tenant_id=tenant_id,
                total_communities=0,
                levels={},
                modularity_score=0.0,
            )

        # 1. Build weighted adjacency graph
        nodes, edges, node_triples = self._build_graph(triples)
        if not nodes:
            return CommunityHierarchy(
                tenant_id=tenant_id,
                total_communities=0,
                levels={},
                modularity_score=0.0,
            )

        # Handle trivial graph with 1 or 2 nodes
        if len(nodes) <= 2:
            single_comm = GraphCommunity(
                community_id=f"comm_lvl0_{uuid.uuid4().hex[:8]}",
                tenant_id=tenant_id,
                level=0,
                title=f"Community: {', '.join(sorted(nodes))}",
                entities=sorted(nodes),
                triples=triples,
                weight=1.0,
                summary=f"Entity cluster containing: {', '.join(sorted(nodes))}",
            )
            return CommunityHierarchy(
                tenant_id=tenant_id,
                total_communities=1,
                levels={0: [single_comm]},
                modularity_score=1.0,
            )

        hierarchy_levels: dict[int, list[GraphCommunity]] = {}
        total_comm_count = 0

        # Current graph representation: (nodes, edges, node_entities_map, node_triples_map)
        current_nodes = list(nodes)
        current_edges = dict(edges)
        node_to_entities: dict[str, set[str]] = {n: {n} for n in current_nodes}
        node_to_triples: dict[str, list[EntityTriple]] = {n: node_triples.get(n, []) for n in current_nodes}

        prev_partition_count = len(current_nodes)

        for level in range(max_levels):
            # Phase 1 & 2: Local moving + Refinement (Leiden partition)
            partition = self._leiden_partition(current_nodes, current_edges)

            # Group nodes into communities
            comm_groups: dict[int, list[str]] = defaultdict(list)
            for node, comm_idx in partition.items():
                comm_groups[comm_idx].append(node)

            # Construct GraphCommunity objects for this level
            level_communities: list[GraphCommunity] = []
            for comm_idx, members in comm_groups.items():
                if len(members) < self.min_community_size and len(comm_groups) > 1:
                    continue

                all_entities: set[str] = set()
                all_triples: list[EntityTriple] = []
                seen_triple_keys: set[tuple[str, str, str]] = set()

                for m in members:
                    all_entities.update(node_to_entities.get(m, {m}))
                    for t in node_to_triples.get(m, []):
                        key = (t.subject.lower(), t.predicate.lower(), t.object.lower())
                        if key not in seen_triple_keys:
                            seen_triple_keys.add(key)
                            all_triples.append(t)

                sorted_entities = sorted(all_entities)
                primary_label = sorted_entities[0] if sorted_entities else f"Cluster {comm_idx}"
                if len(sorted_entities) > 1:
                    comm_title = f"{primary_label} & Related ({len(sorted_entities)} entities)"
                else:
                    comm_title = f"{primary_label} Cluster"

                comm_obj = GraphCommunity(
                    community_id=f"comm_lvl{level}_{uuid.uuid4().hex[:8]}",
                    tenant_id=tenant_id,
                    level=level,
                    title=comm_title,
                    entities=sorted_entities,
                    triples=all_triples,
                    weight=round(len(all_triples) / max(1, len(triples)), 4),
                    summary="",
                )
                level_communities.append(comm_obj)

            if not level_communities:
                break

            hierarchy_levels[level] = level_communities
            total_comm_count += len(level_communities)

            # Check if partition has converged or cannot be aggregated further
            if len(level_communities) <= 1 or len(level_communities) == prev_partition_count:
                break

            prev_partition_count = len(level_communities)

            # Phase 3: Graph Aggregation for next hierarchy level
            next_nodes, next_edges, next_entities, next_triples = self._aggregate_graph(
                current_nodes, current_edges, partition, node_to_entities, node_to_triples
            )
            current_nodes = next_nodes
            current_edges = next_edges
            node_to_entities = next_entities
            node_to_triples = next_triples

        # Calculate final overall modularity
        modularity = self._calculate_modularity(nodes, edges, hierarchy_levels.get(0, []))

        return CommunityHierarchy(
            tenant_id=tenant_id,
            total_communities=total_comm_count,
            levels=hierarchy_levels,
            modularity_score=round(modularity, 4),
            metadata={"node_count": len(nodes), "triple_count": len(triples)},
        )

    def _build_graph(
        self, triples: list[EntityTriple]
    ) -> tuple[set[str], dict[tuple[str, str], float], dict[str, list[EntityTriple]]]:
        """Convert triples into undirected weighted graph."""
        nodes: set[str] = set()
        edges: dict[tuple[str, str], float] = defaultdict(float)
        node_triples: dict[str, list[EntityTriple]] = defaultdict(list)

        for t in triples:
            sub = t.subject.strip()
            obj = t.object.strip()
            if not sub or not obj:
                continue

            nodes.add(sub)
            nodes.add(obj)
            node_triples[sub].append(t)
            node_triples[obj].append(t)

            weight = float(t.confidence or 1.0)
            u, v = sorted([sub, obj])
            edges[(u, v)] += weight

        return nodes, dict(edges), dict(node_triples)

    def _leiden_partition(
        self, nodes: list[str], edges: dict[tuple[str, str], float]
    ) -> dict[str, int]:
        """Leiden modularity partitioning over nodes and weighted edges."""
        sorted_nodes = sorted(nodes)

        # Build node adjacency map and degrees
        adj: dict[str, dict[str, float]] = defaultdict(dict)
        degrees: dict[str, float] = defaultdict(float)
        total_weight = 0.0

        for (u, v), w in edges.items():
            adj[u][v] = w
            adj[v][u] = w
            degrees[u] += w
            degrees[v] += w
            total_weight += w

        m2 = 2.0 * total_weight if total_weight > 0 else 1.0

        # Step 1: Initial singleton partition
        partition: dict[str, int] = {node: i for i, node in enumerate(sorted_nodes)}
        comm_weights: dict[int, float] = {i: degrees[node] for i, node in enumerate(sorted_nodes)}

        # Step 2: Local moving loop
        improved = True
        max_iters = 15
        iteration = 0

        while improved and iteration < max_iters:
            improved = False
            iteration += 1

            for node in sorted_nodes:
                current_comm = partition[node]
                k_i = degrees[node]

                # Weight connected to each neighbor community
                neighbor_comms: dict[int, float] = defaultdict(float)
                for neighbor, weight in adj[node].items():
                    neighbor_comms[partition[neighbor]] += weight

                best_comm = current_comm
                best_gain = 0.0

                # Compute modularity gain of moving node to neighbor communities
                comm_weights[current_comm] -= k_i

                for cand_comm, k_i_in in neighbor_comms.items():
                    tot_cand = comm_weights[cand_comm]
                    # Leiden / Newman-Girvan delta Q formula:
                    # delta_Q = (k_i_in / 2m) - resolution * (k_i * tot_cand / (2m)^2)
                    gain = (k_i_in / m2) - self.resolution * ((k_i * tot_cand) / (m2 * m2))
                    if gain > best_gain:
                        best_gain = gain
                        best_comm = cand_comm

                # Place node into best community
                partition[node] = best_comm
                comm_weights[best_comm] += k_i

                if best_comm != current_comm:
                    improved = True

        # Step 3: Refinement & Re-index communities contiguously
        refined_partition = self._refine_and_reindex(partition, adj)
        return refined_partition

    def _refine_and_reindex(
        self, partition: dict[str, int], adj: dict[str, dict[str, float]]
    ) -> dict[str, int]:
        """Refine partitions into connected sub-components and re-index 0..N."""
        # Find connected components within each community to ensure no disconnected islands
        comm_to_nodes: dict[int, list[str]] = defaultdict(list)
        for node, c in partition.items():
            comm_to_nodes[c].append(node)

        refined: dict[str, int] = {}
        next_comm_id = 0

        for c, members in comm_to_nodes.items():
            # BFS connected components within members
            unvisited = set(members)
            while unvisited:
                start = sorted(unvisited)[0]
                queue = [start]
                unvisited.remove(start)
                refined[start] = next_comm_id

                while queue:
                    curr = queue.pop(0)
                    for nbr in adj[curr]:
                        if nbr in unvisited and partition[nbr] == c:
                            unvisited.remove(nbr)
                            refined[nbr] = next_comm_id
                            queue.append(nbr)

                next_comm_id += 1

        return refined

    def _aggregate_graph(
        self,
        nodes: list[str],
        edges: dict[tuple[str, str], float],
        partition: dict[str, int],
        node_to_entities: dict[str, set[str]],
        node_to_triples: dict[str, list[EntityTriple]],
    ) -> tuple[
        list[str],
        dict[tuple[str, str], float],
        dict[str, set[str]],
        dict[str, list[EntityTriple]],
    ]:
        """Aggregate nodes and edges into super-nodes for higher hierarchy levels."""
        super_nodes: set[str] = set()
        super_edges: dict[tuple[str, str], float] = defaultdict(float)
        super_entities: dict[str, set[str]] = defaultdict(set)
        super_triples: dict[str, list[EntityTriple]] = defaultdict(list)

        for node in nodes:
            c_id = f"super_{partition[node]}"
            super_nodes.add(c_id)
            super_entities[c_id].update(node_to_entities.get(node, {node}))
            super_triples[c_id].extend(node_to_triples.get(node, []))

        for (u, v), w in edges.items():
            cu = f"super_{partition[u]}"
            cv = f"super_{partition[v]}"
            if cu != cv:
                su, sv = sorted([cu, cv])
                super_edges[(su, sv)] += w

        return (
            sorted(super_nodes),
            dict(super_edges),
            dict(super_entities),
            dict(super_triples),
        )

    def _calculate_modularity(
        self,
        nodes: set[str],
        edges: dict[tuple[str, str], float],
        level_0_communities: list[GraphCommunity],
    ) -> float:
        """Compute graph modularity Q for the base partition."""
        if not edges or not level_0_communities:
            return 0.0

        total_m = sum(edges.values())
        if total_m <= 0:
            return 0.0

        # Map entity to community index
        node_comm: dict[str, int] = {}
        for idx, comm in enumerate(level_0_communities):
            for ent in comm.entities:
                node_comm[ent] = idx

        # Degrees
        degrees: dict[str, float] = defaultdict(float)
        for (u, v), w in edges.items():
            degrees[u] += w
            degrees[v] += w

        m2 = 2.0 * total_m
        q = 0.0

        for (u, v), w in edges.items():
            if node_comm.get(u) == node_comm.get(v):
                q += (w / total_m) - (degrees[u] * degrees[v]) / (m2 * m2)

        return max(0.0, min(1.0, q))
