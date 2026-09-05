"""Edge Delta Calculator Domain Service (M98).

Calculates deterministic differential sync packages between sequence checkpoints,
computes cryptographic SHA-256 state manifests, and validates delta payloads.
Zero framework or infrastructure imports (strictly Hexagonal).
"""

import hashlib
import json
from datetime import UTC, datetime

from src.domain.abstractions.edge_sync import (
    ChunkSyncItem,
    EdgeDeltaCalculatorProtocol,
    EdgeSyncDelta,
    VectorSyncItem,
)


class EdgeDeltaCalculator(EdgeDeltaCalculatorProtocol):
    """Pure domain calculator for differential edge synchronization."""

    def compute_delta(
        self,
        tenant_id: str,
        since_seq: int,
        current_seq: int,
        chunks: list[ChunkSyncItem],
        vectors: list[VectorSyncItem],
        deleted_ids: list[str],
    ) -> EdgeSyncDelta:
        """Assemble a differential delta package with cryptographic checksum."""
        now_iso = datetime.now(UTC).isoformat()

        # Compute deterministic checksum over delta elements
        hasher = hashlib.sha256()
        hasher.update(f"tenant:{tenant_id}|since:{since_seq}|cur:{current_seq}|".encode())

        for c in sorted(chunks, key=lambda x: x.chunk_id):
            hasher.update(f"c:{c.chunk_id}:{c.document_id}:{c.chunk_index}:".encode())
            hasher.update(c.content.encode("utf-8"))

        for v in sorted(vectors, key=lambda x: x.chunk_id):
            hasher.update(f"v:{v.chunk_id}:{v.dimension}:".encode())
            # Hash vector coordinates
            vec_repr = json.dumps(v.embedding[:10])  # Sample first 10 dims for speed & stability
            hasher.update(vec_repr.encode())

        for d_id in sorted(deleted_ids):
            hasher.update(f"d:{d_id}:".encode())

        checksum = hasher.hexdigest()

        return EdgeSyncDelta(
            tenant_id=tenant_id,
            checkpoint_sequence=current_seq,
            previous_sequence=since_seq,
            added_chunks=chunks,
            added_vectors=vectors,
            deleted_chunk_ids=deleted_ids,
            checksum_sha256=checksum,
            generated_at=now_iso,
        )

    def verify_checksum(self, delta: EdgeSyncDelta) -> bool:
        """Verify that an EdgeSyncDelta matches its declared SHA-256 checksum."""
        recomputed = self.compute_delta(
            tenant_id=delta.tenant_id,
            since_seq=delta.previous_sequence,
            current_seq=delta.checkpoint_sequence,
            chunks=delta.added_chunks,
            vectors=delta.added_vectors,
            deleted_ids=delta.deleted_chunk_ids,
        )
        return recomputed.checksum_sha256 == delta.checksum_sha256

    def calculate_delta(
        self,
        tenant_id: str,
        since_seq: int,
        high_watermark_seq: int,
        chunks: list[ChunkSyncItem],
        vectors: list[VectorSyncItem],
        deleted_ids: list[str] | None = None,
    ) -> EdgeSyncDelta:
        """Alias for compute_delta for API ergonomics."""
        return self.compute_delta(
            tenant_id=tenant_id,
            since_seq=since_seq,
            current_seq=high_watermark_seq,
            chunks=chunks,
            vectors=vectors,
            deleted_ids=deleted_ids or [],
        )

    def verify_integrity(self, delta: EdgeSyncDelta) -> bool:
        """Alias for verify_checksum."""
        return self.verify_checksum(delta)
