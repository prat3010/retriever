# GraphRAG HDBSCAN Community Clustering & Knowledge Synthesis

**Milestone:** M81 (v0.66.0)  
**System Layer:** Unsupervised Knowledge Graph Clustering & Community Summarization (Platform Battery #6)  
**Architecture:** HDBSCAN Density Clustering + Mutual Reachability Metric + Minimum Spanning Tree (MST) + Hierarchical Cluster Extraction  

---

## 1. Executive Summary

Milestone 81 establishes **Platform Battery #6: `graphrag_hdbscan_clustering`**, delivering unsupervised semantic community discovery across knowledge graph entities.

Traditional GraphRAG architectures often rely on algorithms like Louvain, Leiden, or $k$-Means to group related entities into conceptual communities. However, these methods exhibit serious shortcomings in real-world enterprise corpora:
- $k$-Means requires specifying an arbitrary number of clusters ($k$) in advance, which is impossible for arbitrary document collections.
- Louvain/Leiden can force isolated outliers and unrelated entities into existing communities, distorting topic boundaries.
- Density variations across disparate document domains lead to poor cluster quality.

Platform Battery #6 deploys **HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise)** directly over entity embeddings. HDBSCAN requires no predetermined cluster count, automatically classifies noisy/peripheral entities as outliers, and discovers semantic communities of varying densities across multi-hop entity relationships.

---

## 2. Mathematical Foundation & Mutual Reachability Graph

Given a set of entity embedding vectors $X = \{x_1, x_2, \dots, x_n\}$ in $\mathbb{R}^d$:

### 1. Core Distance
For each entity $x$, its core distance $d_{\text{core}}(x)$ is the Euclidean distance to its $k$-th nearest neighbor (where $k = \text{min\_cluster\_size}$):

$$d_{\text{core}}(x) = \text{dist}(x, \text{NN}_k(x))$$

### 2. Mutual Reachability Distance
To lower density variations, the mutual reachability distance $d_{\text{mreach}}(a, b)$ between entities $a$ and $b$ is defined as:

$$d_{\text{mreach}}(a, b) = \max \left\{ d_{\text{core}}(a), d_{\text{core}}(b), \text{dist}(a, b) \right\}$$

```text
       Dense Region                      Sparse Region
      (Small d_core)                    (Large d_core)
       •   •   •                              o
         • a •                                  \
           │                                     \ dist(a, b)
           └────────────────────────────────────── b
      d_mreach(a, b) = max(d_core(a), d_core(b), dist(a, b))
```

This transforms the metric space: dense clusters remain tightly bonded, while noise points are pushed further away.

### 3. Minimum Spanning Tree (MST) & Cluster Stability
HDBSCAN constructs a Minimum Spanning Tree over the mutual reachability graph, converts it into a cluster hierarchy tree, and condenses clusters based on **excess of mass** ($\lambda = 1/\text{distance}$). Clusters with the highest persistence throughout the hierarchy are selected as stable enterprise knowledge communities.

---

## 3. Community Summarization & Query Flow

1. **Entity Extraction:** Extracts typed entities and relationships (e.g. `(Micro-Enclave)-[AUTHENTICATES]->(PCR0)`) during ingestion.
2. **HDBSCAN Partitioning:** Automatically clusters entity embeddings into $C_1, C_2, \dots, C_m$ communities, labeling unclassifiable nodes as noise (Cluster $-1$).
3. **Hierarchical Summarization:** Generates an executive summary for each community using a background LLM routine, pre-grounding high-level theme questions (e.g. "What are the major security architectures in this repository?").

---

## 4. Implementation Details

- **Adapter:** `apps/api/src/adapters/cognitive/topic_clustering_adapter.py`
- **Core Parameters:**
  - `min_cluster_size`: $3$
  - `metric`: `"euclidean"`
  - `cluster_selection_epsilon`: $0.15$
  - `cluster_selection_method`: `"eom"` (Excess of Mass)
- **Latency Profile:** $\sim 35\text{ms}$ for graphs of 500+ entities.
- **Health Check Endpoint:** `GET /v1/graph/communities`

---

## 5. Non-Negotiable Invariants

1. **Noise Isolation:** Entities categorized as noise (Cluster $-1$) must never be forced into a topic summary; they are queried only via standard direct vector similarity.
2. **Deterministic Clustering:** Random seeds and ordering are pinned to produce identical cluster assignments across multiple runs on unchanged graphs.
3. **Strict Multi-Tenancy:** HDBSCAN runs strictly within isolated tenant namespaces; entity vectors from different tenants are never co-clustered.
