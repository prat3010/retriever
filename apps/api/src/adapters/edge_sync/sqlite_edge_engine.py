"""Production-grade embedded SQLite engine for offline vector and hybrid search (M98).

Implements pure embedded FTS5 full-text keyword indexing and binary BLOB
vector storage with in-process NumPy cosine similarity computation.
Zero external microservice dependencies, 100% sovereign and offline-first.
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

import numpy as np

from src.domain.abstractions.edge_sync import (
    EdgeDatabaseEngineProtocol,
    EdgeMutation,
    EdgeSearchRequest,
    EdgeSearchResponse,
    EdgeSearchResultItem,
    EdgeSyncDelta,
    OfflineExecutionTier,
)
from src.domain.edge_sync.fusion_ranker import EdgeFusionRanker

logger = logging.getLogger(__name__)


class SqliteEdgeEngine(EdgeDatabaseEngineProtocol):
    """Production-grade embedded SQLite engine for offline vector and hybrid search."""

    def __init__(self, db_path: str = ":memory:", ranker: EdgeFusionRanker | None = None) -> None:
        self.db_path = db_path
        self.ranker = ranker or EdgeFusionRanker(rrf_k=60)
        self._memory_conn: sqlite3.Connection | None = None

    def _get_connection(self, path: str | None = None) -> sqlite3.Connection:
        target = path or self.db_path
        if target == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(":memory:")
            return self._memory_conn
        p = Path(target)
        p.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(target)

    def initialize_schema(self, db_path: str | None = None) -> None:
        """Create standard sovereign edge database tables and FTS5 virtual table."""
        conn = self._get_connection(db_path)
        cursor = conn.cursor()

        # 1. Edge Configuration & Checkpoint Tracker
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS edge_config (
                tenant_id TEXT PRIMARY KEY,
                last_sync_seq INTEGER NOT NULL DEFAULT 0,
                checksum TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            """
        )

        # 2. Documents
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content_hash TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

        # 3. Document Chunks
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL DEFAULT 0,
                meta_data_json TEXT NOT NULL DEFAULT '{}'
            );
            """
        )

        # 4. FTS5 Full-Text Search Virtual Table
        cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                chunk_id UNINDEXED,
                content,
                tokenize = 'porter unicode61'
            );
            """
        )

        # 5. Vector Records (stored as raw binary float32 blobs)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vector_records (
                chunk_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                dimension INTEGER NOT NULL DEFAULT 768,
                embedding_blob BLOB NOT NULL
            );
            """
        )

        # 6. Offline Pending Mutations Queue
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS offline_mutations (
                mutation_id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                action TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                lamport_timestamp INTEGER NOT NULL DEFAULT 0,
                device_timestamp TEXT NOT NULL,
                synced INTEGER NOT NULL DEFAULT 0
            );
            """
        )

        conn.commit()
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()

    def apply_delta(self, *args: Any, **kwargs: Any) -> int:
        """Apply differential delta package to the SQLite edge database.
        
        Supports both apply_delta(delta) and apply_delta(db_path, delta).
        """
        db_path: str | None = None
        delta: EdgeSyncDelta | None = None

        if len(args) == 1:
            if isinstance(args[0], EdgeSyncDelta):
                delta = args[0]
            elif isinstance(args[0], str):
                db_path = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], str) and isinstance(args[1], EdgeSyncDelta):
                db_path, delta = args[0], args[1]
            elif isinstance(args[0], EdgeSyncDelta):
                delta = args[0]
                db_path = str(args[1]) if len(args) > 1 else None

        if "delta" in kwargs:
            delta = kwargs["delta"]
        if "db_path" in kwargs:
            db_path = kwargs["db_path"]

        if delta is None:
            raise ValueError("EdgeSyncDelta parameter is required")

        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()

        # Handle deletions
        for c_id in delta.deleted_chunk_ids:
            cursor.execute("DELETE FROM document_chunks WHERE chunk_id = ?", (c_id,))
            cursor.execute("DELETE FROM vector_records WHERE chunk_id = ?", (c_id,))
            cursor.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (c_id,))

        # Handle chunk insertions / updates
        vector_dict: dict[str, list[float]] = {v.chunk_id: v.embedding for v in delta.added_vectors}

        for chunk in delta.added_chunks:
            meta_json = json.dumps(chunk.meta_data)
            cursor.execute(
                """
                INSERT OR REPLACE INTO document_chunks
                (chunk_id, tenant_id, document_id, chunk_index, content, token_count, meta_data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk.chunk_id,
                    delta.tenant_id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.content,
                    chunk.token_count,
                    meta_json,
                ),
            )

            # Upsert into FTS5
            cursor.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (chunk.chunk_id,))
            cursor.execute(
                "INSERT INTO fts_chunks (chunk_id, content) VALUES (?, ?)",
                (chunk.chunk_id, chunk.content),
            )

            # Vector record
            if chunk.chunk_id in vector_dict:
                emb = vector_dict[chunk.chunk_id]
                arr = np.array(emb, dtype=np.float32)
                blob = arr.tobytes()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO vector_records
                    (chunk_id, tenant_id, dimension, embedding_blob)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chunk.chunk_id, delta.tenant_id, len(emb), blob),
                )

        # Update edge_config checkpoint sequence
        cursor.execute(
            """
            INSERT OR REPLACE INTO edge_config
            (tenant_id, last_sync_seq, checksum, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            """,
            (delta.tenant_id, delta.checkpoint_sequence, delta.checksum_sha256),
        )

        conn.commit()
        count = len(delta.added_chunks)
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()

        return count

    def get_synced_sequence(self, db_path: str | None = None) -> int:
        """Fetch current high watermark synced sequence number from edge_config."""
        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_sync_seq FROM edge_config ORDER BY updated_at DESC LIMIT 1")
        row = cursor.fetchone()
        seq = row[0] if row else 0
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()
        return seq

    def search_hybrid(self, *args: Any, **kwargs: Any) -> EdgeSearchResponse:
        """Execute local hybrid search (vector cosine + FTS5 BM25) over edge SQLite database.
        
        Supports search_hybrid(request), search_hybrid(db_path, request), and search_hybrid(request, db_path).
        """
        db_path: str | None = None
        request: EdgeSearchRequest | None = None

        if len(args) == 1:
            if isinstance(args[0], EdgeSearchRequest):
                request = args[0]
            elif isinstance(args[0], str):
                db_path = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], str) and isinstance(args[1], EdgeSearchRequest):
                db_path, request = args[0], args[1]
            elif isinstance(args[0], EdgeSearchRequest):
                request = args[0]
                db_path = str(args[1]) if len(args) > 1 else None

        if "request" in kwargs:
            request = kwargs["request"]
        if "db_path" in kwargs:
            db_path = kwargs["db_path"]

        if request is None:
            raise ValueError("EdgeSearchRequest parameter is required")

        start_time = time.perf_counter()
        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()

        # 1. Fetch chunks metadata map
        cursor.execute("SELECT chunk_id, document_id, content, meta_data_json FROM document_chunks")
        chunk_rows = cursor.fetchall()
        chunk_map: dict[str, dict[str, Any]] = {}
        for r in chunk_rows:
            chunk_id, doc_id, content, meta_json = r
            try:
                meta = json.loads(meta_json)
            except Exception:
                meta = {}
            chunk_map[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": doc_id,
                "content": content,
                "meta_data": meta,
            }

        # 2. Vector Search (if query embedding provided)
        vector_candidates: list[dict[str, Any]] = []
        if request.query_embedding is not None and len(request.query_embedding) > 0:
            query_vec = np.array(request.query_embedding, dtype=np.float32)
            norm_q = np.linalg.norm(query_vec)
            if norm_q > 0:
                query_vec = query_vec / norm_q

            cursor.execute("SELECT chunk_id, dimension, embedding_blob FROM vector_records")
            vec_rows = cursor.fetchall()

            if vec_rows:
                chunk_ids = []
                vec_list = []
                for r in vec_rows:
                    c_id, _dim, blob = r
                    arr = np.frombuffer(blob, dtype=np.float32)
                    if len(arr) == len(query_vec):
                        chunk_ids.append(c_id)
                        vec_list.append(arr)

                if vec_list:
                    mat = np.stack(vec_list)
                    norms = np.linalg.norm(mat, axis=1, keepdims=True)
                    norms[norms == 0] = 1e-8
                    mat_norm = mat / norms

                    sims = np.dot(mat_norm, query_vec)
                    ranked_indices = np.argsort(sims)[::-1][: max(request.top_k * 2, 20)]

                    for idx in ranked_indices:
                        c_id = chunk_ids[idx]
                        if c_id in chunk_map:
                            item = dict(chunk_map[c_id])
                            item["score"] = float(sims[idx])
                            item["vector_score"] = float(sims[idx])
                            vector_candidates.append(item)

        # 3. FTS5 Full-Text Keyword Search
        keyword_candidates: list[dict[str, Any]] = []
        clean_query = "".join([c if c.isalnum() or c.isspace() else " " for c in request.query]).strip()
        if clean_query:
            tokens = clean_query.split()
            fts_query = " OR ".join(tokens)
            try:
                cursor.execute(
                    """
                    SELECT chunk_id, rank
                    FROM fts_chunks
                    WHERE fts_chunks MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, max(request.top_k * 2, 20)),
                )
                fts_rows = cursor.fetchall()
                for r in fts_rows:
                    c_id, rank_score = r
                    if c_id in chunk_map:
                        item = dict(chunk_map[c_id])
                        # FTS5 rank is negative (lower = better), normalize to positive score
                        bm25_sim = float(1.0 / (1.0 + abs(rank_score)))
                        item["score"] = bm25_sim
                        item["bm25_score"] = bm25_sim
                        keyword_candidates.append(item)
            except sqlite3.OperationalError as e:
                logger.warning(f"FTS5 query syntax error for '{fts_query}': {e}")

        # 4. Fusion Ranking
        use_hybrid_mode = request.use_hybrid and bool(vector_candidates and keyword_candidates)
        if use_hybrid_mode:
            fused = self.ranker.fuse_results(
                vector_results=vector_candidates,
                fts_results=keyword_candidates,
                top_k=request.top_k,
                use_rrf=True,
            )
        elif vector_candidates:
            fused = [
                EdgeSearchResultItem(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    content=c["content"],
                    score=c.get("score", 0.0),
                    vector_score=c.get("score", 0.0),
                    bm25_score=0.0,
                    match_type="vector",
                    meta_data=c.get("meta_data", {}),
                )
                for c in vector_candidates[: request.top_k]
            ]
        elif keyword_candidates:
            fused = [
                EdgeSearchResultItem(
                    chunk_id=c["chunk_id"],
                    document_id=c["document_id"],
                    content=c["content"],
                    score=c.get("score", 0.0),
                    vector_score=0.0,
                    bm25_score=c.get("score", 0.0),
                    match_type="bm25",
                    meta_data=c.get("meta_data", {}),
                )
                for c in keyword_candidates[: request.top_k]
            ]
        else:
            fused = []

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()

        synthesized_answer = (
            f"Edge retrieved {len(fused)} items in {elapsed_ms:.1f}ms (hybrid={use_hybrid_mode})."
            if fused
            else "No matching documents found on edge."
        )

        return EdgeSearchResponse(
            results=fused,
            total_hits=len(fused),
            latency_ms=round(elapsed_ms, 2),
            source="local_sqlite",
            execution_tier=OfflineExecutionTier.GROUNDED_EXTRACTION,
            synthesized_answer=synthesized_answer,
        )

    def search(self, *args: Any, **kwargs: Any) -> EdgeSearchResponse:
        """Alias to search_hybrid for convenience."""
        return self.search_hybrid(*args, **kwargs)

    def record_mutation(self, *args: Any, **kwargs: Any) -> None:
        """Record an offline mutation into the local SQLite pending queue.
        
        Supports record_mutation(mutation) and record_mutation(db_path, mutation).
        """
        db_path: str | None = None
        mutation: EdgeMutation | None = None

        if len(args) == 1:
            if isinstance(args[0], EdgeMutation):
                mutation = args[0]
            elif isinstance(args[0], str):
                db_path = args[0]
        elif len(args) >= 2:
            if isinstance(args[0], str) and isinstance(args[1], EdgeMutation):
                db_path, mutation = args[0], args[1]
            elif isinstance(args[0], EdgeMutation):
                mutation = args[0]
                db_path = str(args[1]) if len(args) > 1 else None

        if "mutation" in kwargs:
            mutation = kwargs["mutation"]
        if "db_path" in kwargs:
            db_path = kwargs["db_path"]

        if mutation is None:
            raise ValueError("EdgeMutation parameter is required")

        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO offline_mutations
            (mutation_id, tenant_id, node_id, entity_type, action, payload_json, lamport_timestamp, device_timestamp, synced)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                mutation.mutation_id,
                mutation.tenant_id,
                mutation.node_id,
                mutation.entity_type,
                mutation.action,
                json.dumps(mutation.payload),
                mutation.lamport_timestamp,
                mutation.device_timestamp,
            ),
        )
        conn.commit()
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()

    def get_pending_mutations(self, db_path: str | None = None) -> list[EdgeMutation]:
        """Fetch all pending unsynced offline mutations."""
        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT mutation_id, tenant_id, node_id, entity_type, action, payload_json, lamport_timestamp, device_timestamp
            FROM offline_mutations
            WHERE synced = 0
            ORDER BY lamport_timestamp ASC
            """
        )
        rows = cursor.fetchall()
        mutations: list[EdgeMutation] = []
        for r in rows:
            m_id, t_id, n_id, e_type, act, p_json, l_ts, d_ts = r
            try:
                payload = json.loads(p_json)
            except Exception:
                payload = {}
            mutations.append(
                EdgeMutation(
                    mutation_id=m_id,
                    tenant_id=t_id,
                    node_id=n_id,
                    entity_type=e_type,
                    action=act,
                    payload=payload,
                    lamport_timestamp=l_ts,
                    device_timestamp=d_ts,
                )
            )
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()
        return mutations

    def purge_synced_mutations(self, mutation_ids: list[str], db_path: str | None = None) -> None:
        """Purge or mark mutations as synced."""
        self.initialize_schema(db_path)
        conn = self._get_connection(db_path)
        cursor = conn.cursor()
        for m_id in mutation_ids:
            cursor.execute("DELETE FROM offline_mutations WHERE mutation_id = ?", (m_id,))
        conn.commit()
        if db_path and db_path != ":memory:" and conn != self._memory_conn:
            conn.close()

    def mark_mutations_synced(self, db_path: str, mutation_ids: list[str]) -> None:
        """Alias to purge_synced_mutations."""
        self.purge_synced_mutations(mutation_ids=mutation_ids, db_path=db_path)
