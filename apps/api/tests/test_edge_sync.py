"""Comprehensive Pytest Test Suite for Sovereign Edge SQLite & Vector Sync Engine (M98).

Verifies:
- EdgeDeltaCalculator differential computation and SHA-256 integrity verification
- EdgeFusionRanker Reciprocal Rank Fusion (RRF) and hybrid score weighting
- SqliteEdgeEngine embedded FTS5 full-text search, BLOB vector cosine similarity, and mutations
- EdgeSyncAdapter standalone .sqlite bundle creation and manifest emission
- EdgeMutationReconciler Lamport timestamp offline mutation reconciliation and tenant isolation
- Platform Battery #18 (sovereign_edge_sync) active status and category verification
- FastAPI REST endpoints: node registration, delta pull, bundle download, mutation reconciliation, edge search
"""

import os
import sqlite3
import tempfile
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.adapters.edge_sync.edge_mutation_reconciler import EdgeMutationReconciler
from src.adapters.edge_sync.edge_sync_adapter import EdgeSyncAdapter
from src.adapters.edge_sync.sqlite_edge_engine import SqliteEdgeEngine
from src.config import settings
from src.container import container
from src.domain.abstractions.batteries import BatteryCategory, BatteryStatus
from src.domain.abstractions.edge_sync import (
    ChunkSyncItem,
    EdgeBundleManifest,
    EdgeMutation,
    EdgeSearchRequest,
    EdgeSyncDelta,
    OfflineExecutionTier,
    VectorSyncItem,
)
from src.domain.edge_sync.delta_calculator import EdgeDeltaCalculator
from src.domain.edge_sync.fusion_ranker import EdgeFusionRanker
from src.main import app

client = TestClient(app)

TEST_TENANT_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_KEY = settings.ADMIN_MASTER_KEY


# ---------------------------------------------------------------------------
# Unit Tests: Delta Calculator & Integrity
# ---------------------------------------------------------------------------


def test_delta_calculator_empty_delta():
    calc = EdgeDeltaCalculator()
    delta = calc.calculate_delta(
        tenant_id=TEST_TENANT_ID,
        since_seq=0,
        high_watermark_seq=0,
        chunks=[],
        vectors=[],
    )
    assert delta.tenant_id == TEST_TENANT_ID
    assert delta.since_seq == 0
    assert delta.high_watermark_seq == 0
    assert delta.total_chunks == 0
    assert len(delta.checksum_sha256) == 64
    assert calc.verify_integrity(delta) is True


def test_delta_calculator_with_payload_and_tampering():
    calc = EdgeDeltaCalculator()
    chunk = ChunkSyncItem(
        chunk_id="chk_1",
        document_id="doc_1",
        chunk_index=0,
        content="Retrieval Augmented Generation with Sovereign Edge",
        sequence_num=1,
    )
    vec = VectorSyncItem(
        chunk_id="chk_1",
        embedding=[0.1] * 768,
        dimension=768,
    )

    delta = calc.calculate_delta(
        tenant_id=TEST_TENANT_ID,
        since_seq=0,
        high_watermark_seq=1,
        chunks=[chunk],
        vectors=[vec],
    )

    assert delta.total_chunks == 1
    assert calc.verify_integrity(delta) is True

    # Tamper with chunk content -> verify failure
    tampered_delta = EdgeSyncDelta(
        tenant_id=delta.tenant_id,
        previous_sequence=delta.previous_sequence,
        checkpoint_sequence=delta.checkpoint_sequence,
        added_chunks=[
            ChunkSyncItem(
                chunk_id="chk_1",
                document_id="doc_1",
                chunk_index=0,
                content="Tampered malicious content",
                sequence_num=1,
            )
        ],
        added_vectors=delta.added_vectors,
        checksum_sha256=delta.checksum_sha256,
    )
    assert calc.verify_integrity(tampered_delta) is False


# ---------------------------------------------------------------------------
# Unit Tests: Edge Fusion Ranker
# ---------------------------------------------------------------------------


def test_edge_fusion_ranker_rrf():
    ranker = EdgeFusionRanker(rrf_k=60)
    vector_results = [
        {"chunk_id": "c1", "content": "RAG Architecture", "vector_score": 0.95, "document_id": "d1"},
        {"chunk_id": "c2", "content": "Edge SQLite Storage", "vector_score": 0.85, "document_id": "d2"},
    ]
    fts_results = [
        {"chunk_id": "c2", "content": "Edge SQLite Storage", "fts_score": 0.9, "document_id": "d2"},
        {"chunk_id": "c3", "content": "Cloud PgVector", "fts_score": 0.8, "document_id": "d3"},
    ]

    fused = ranker.fuse_results(vector_results, fts_results, top_k=3, use_rrf=True)
    assert len(fused) == 3
    assert fused[0].chunk_id == "c2"
    assert fused[0].match_type == "hybrid"


# ---------------------------------------------------------------------------
# Unit Tests: Embedded SQLite Edge Engine (FTS5 + Binary BLOB Vector)
# ---------------------------------------------------------------------------


def test_sqlite_edge_engine_fts5_and_vector():
    engine = SqliteEdgeEngine(db_path=":memory:")
    engine.initialize_schema()

    v1 = np.zeros(768, dtype=np.float32)
    v1[0] = 1.0
    v2 = np.zeros(768, dtype=np.float32)
    v2[1] = 1.0

    chunks = [
        ChunkSyncItem(
            chunk_id="chunk_alpha",
            document_id="doc_alpha",
            chunk_index=0,
            content="Autonomous AI edge agents deploy on sovereign SQLite nodes",
            meta_data={"category": "ai"},
            sequence_num=10,
        ),
        ChunkSyncItem(
            chunk_id="chunk_beta",
            document_id="doc_beta",
            chunk_index=0,
            content="PostgreSQL pgvector handles centralized cloud storage",
            meta_data={"category": "cloud"},
            sequence_num=11,
        ),
    ]
    vectors = [
        VectorSyncItem(chunk_id="chunk_alpha", embedding=v1.tolist(), dimension=768),
        VectorSyncItem(chunk_id="chunk_beta", embedding=v2.tolist(), dimension=768),
    ]

    calc = EdgeDeltaCalculator()
    delta = calc.calculate_delta(
        tenant_id=TEST_TENANT_ID,
        since_seq=0,
        high_watermark_seq=11,
        chunks=chunks,
        vectors=vectors,
    )

    applied_count = engine.apply_delta(delta)
    assert applied_count == 2
    assert engine.get_synced_sequence() == 11

    # 1. Test FTS5 exact keyword match
    fts_req = EdgeSearchRequest(
        query="autonomous agent sovereign",
        top_k=5,
        use_hybrid=False,
    )
    fts_resp = engine.search(fts_req)
    assert len(fts_resp.results) >= 1
    assert fts_resp.results[0].chunk_id == "chunk_alpha"

    # 2. Test Vector cosine search via query_embedding
    q_vec = np.zeros(768, dtype=np.float32)
    q_vec[0] = 0.99
    q_vec[2] = 0.05
    q_vec /= np.linalg.norm(q_vec)

    vec_req = EdgeSearchRequest(
        query="does not match text directly",
        query_embedding=q_vec.tolist(),
        top_k=5,
        use_hybrid=False,
    )
    vec_resp = engine.search(vec_req)
    assert len(vec_resp.results) >= 1
    assert vec_resp.results[0].chunk_id == "chunk_alpha"
    assert vec_resp.results[0].vector_score > 0.9

    # 3. Test Hybrid Fusion
    hybrid_req = EdgeSearchRequest(
        query="SQLite nodes",
        query_embedding=q_vec.tolist(),
        top_k=5,
        use_hybrid=True,
    )
    hybrid_resp = engine.search(hybrid_req)
    assert len(hybrid_resp.results) >= 1
    assert hybrid_resp.results[0].chunk_id == "chunk_alpha"


def test_sqlite_edge_engine_mutations():
    engine = SqliteEdgeEngine(db_path=":memory:")
    engine.initialize_schema()

    mut = EdgeMutation(
        mutation_id="mut_100",
        tenant_id=TEST_TENANT_ID,
        node_id="node_field_mac",
        entity_type="field_note",
        action="insert",
        payload={"text": "Inspected turbine on site; running smoothly"},
        lamport_timestamp=1,
    )

    engine.record_mutation(mut)

    pending = engine.get_pending_mutations()
    assert len(pending) == 1
    assert pending[0].mutation_id == "mut_100"
    assert pending[0].payload["text"] == "Inspected turbine on site; running smoothly"

    engine.purge_synced_mutations(["mut_100"])
    assert len(engine.get_pending_mutations()) == 0


# ---------------------------------------------------------------------------
# Unit Tests: Standalone Bundle Creation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.adapters.edge_sync.edge_sync_adapter.tenant_session")
async def test_edge_sync_adapter_bundle_creation(mock_tenant_session):
    # Mock database session
    mock_session = AsyncMock()
    mock_res_docs = MagicMock()
    mock_res_docs.scalars.return_value.all.return_value = []
    mock_res_chunks = MagicMock()
    mock_res_chunks.scalars.return_value.all.return_value = []
    mock_res_vecs = MagicMock()
    mock_res_vecs.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[mock_res_docs, mock_res_chunks, mock_res_vecs])
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    adapter = EdgeSyncAdapter()
    manifest = await adapter.create_standalone_bundle(tenant_id=TEST_TENANT_ID)

    assert manifest.tenant_id == TEST_TENANT_ID
    assert manifest.sqlite_version.startswith("3.")
    assert os.path.exists(manifest.bundle_path)
    assert os.path.getsize(manifest.bundle_path) > 0
    assert len(manifest.checksum_sha256) == 64

    conn = sqlite3.connect(manifest.bundle_path)
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    conn.close()

    assert "document_chunks" in tables
    assert "vector_records" in tables
    assert "edge_config" in tables

    try:
        os.unlink(manifest.bundle_path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Unit Tests: Mutation Reconciler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.adapters.edge_sync.edge_mutation_reconciler.tenant_session")
async def test_edge_mutation_reconciler_tenant_mismatch(mock_tenant_session):
    mock_session = AsyncMock()
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    reconciler = EdgeMutationReconciler()
    mutation = EdgeMutation(
        mutation_id="mut_evil",
        tenant_id="99999999-9999-9999-9999-999999999999",  # Attacker tenant
        node_id="rogue_node",
        entity_type="feedback",
        action="insert",
        payload={"message_id": str(uuid.uuid4()), "rating": 1},
        lamport_timestamp=5,
    )

    resolutions = await reconciler.reconcile_mutations(
        tenant_id=TEST_TENANT_ID,  # Victim caller tenant
        mutations=[mutation],
    )
    assert len(resolutions) == 1
    assert resolutions[0].status == "discarded"
    assert resolutions[0].resolution_strategy == "tenant_mismatch_rejected"


# ---------------------------------------------------------------------------
# Unit Tests: Platform Battery #18 Registration
# ---------------------------------------------------------------------------


def test_platform_battery_18_registered():
    battery = container.battery_service.get_battery("sovereign_edge_sync")
    assert battery is not None
    assert battery.id == "sovereign_edge_sync"
    assert battery.category == BatteryCategory.EDGE_DISTRIBUTION
    assert battery.status == BatteryStatus.ACTIVE
    assert "M98" in battery.milestone
    assert "FTS5" in battery.algorithm_foundation
    assert battery.health_check_endpoint == "/v1/admin/edge/overview"


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------


@patch("src.routers.edge.tenant_session")
def test_admin_edge_overview_endpoint(mock_tenant_session):
    mock_session = AsyncMock()
    mock_res_nodes = MagicMock()
    mock_res_nodes.scalars.return_value.all.return_value = []
    mock_res_ckpt = MagicMock()
    mock_res_ckpt.scalar.return_value = 0
    mock_session.execute = AsyncMock(side_effect=[mock_res_nodes, mock_res_ckpt])
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    resp = client.get(
        "/v1/admin/edge/overview",
        headers={"X-Admin-Master-Key": ADMIN_KEY},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_nodes" in data
    assert "online_nodes" in data
    assert "battery" in data
    assert data["battery"]["id"] == "sovereign_edge_sync"


@patch("src.routers.edge.tenant_session")
def test_tenant_edge_node_registration_and_list(mock_tenant_session):
    node_id = f"test_node_{uuid.uuid4().hex[:8]}"
    payload = {
        "node_id": node_id,
        "device_name": "Field Toughbook M3",
        "platform": "darwin_arm64",
        "tier": OfflineExecutionTier.HYBRID_CACHE.value,
        "client_version": "0.83.0",
        "hardware_specs": {"ram_gb": 16, "cores": 8},
    }

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=None)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    mock_res = MagicMock()
    mock_node = MagicMock()
    mock_node.node_id = node_id
    mock_node.tenant_id = uuid.UUID(TEST_TENANT_ID)
    mock_node.device_name = "Field Toughbook M3"
    mock_node.platform = "darwin_arm64"
    mock_node.last_synced_seq = 0
    mock_node.last_heartbeat_at = datetime.now(UTC)
    mock_node.meta_data = {"tier": "hybrid_cache"}

    mock_res.scalars.return_value.all.return_value = [mock_node]
    mock_session.execute = AsyncMock(return_value=mock_res)
    mock_tenant_session.return_value.__aenter__.return_value = mock_session

    # Register node
    reg_resp = client.post(
        f"/v1/tenants/{TEST_TENANT_ID}/edge/nodes/register",
        json=payload,
        headers={"X-Admin-Master-Key": ADMIN_KEY},
    )
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["node_id"] == node_id
    assert reg_data["status"] == "online"
    assert reg_data["tier"] == OfflineExecutionTier.HYBRID_CACHE.value

    # List nodes
    list_resp = client.get(
        f"/v1/tenants/{TEST_TENANT_ID}/edge/nodes",
        headers={"X-Admin-Master-Key": ADMIN_KEY},
    )
    assert list_resp.status_code == 200
    nodes = list_resp.json()
    assert any(n["node_id"] == node_id for n in nodes)


def test_tenant_edge_delta_endpoint():
    mock_delta = EdgeSyncDelta(
        tenant_id=TEST_TENANT_ID,
        checkpoint_sequence=5,
        previous_sequence=0,
        added_chunks=[],
        added_vectors=[],
        deleted_chunk_ids=[],
        checksum_sha256="abcdef1234567890" * 4,
    )
    with patch.object(container.edge_sync_adapter, "get_delta_for_tenant", AsyncMock(return_value=mock_delta)):
        resp = client.get(
            f"/v1/tenants/{TEST_TENANT_ID}/edge/delta?since_seq=0&limit=100",
            headers={"X-Admin-Master-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200
        delta = resp.json()
        assert delta["tenant_id"] == TEST_TENANT_ID
        assert "checksum_sha256" in delta
        assert "added_chunks" in delta
        assert "added_vectors" in delta


def test_tenant_edge_bundle_manifest_and_download():
    # Create temp sqlite file for download testing
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as f:
        f.write(b"SQLite format 3\x00" + b"\x00" * 96)
        temp_path = f.name

    mock_manifest = EdgeBundleManifest(
        bundle_id="b_123",
        tenant_id=TEST_TENANT_ID,
        database_engine="sqlite3",
        total_documents=1,
        total_chunks=2,
        total_vectors=2,
        vector_dimension=768,
        checkpoint_sequence=2,
        checksum_sha256="abc" * 20 + "1234",
        created_at="2026-09-05T00:00:00Z",
        file_size_bytes=1024,
        bundle_path=temp_path,
    )

    with patch.object(container.edge_sync_adapter, "create_standalone_bundle", AsyncMock(return_value=mock_manifest)):
        # 1. Manifest JSON endpoint
        resp = client.post(
            f"/v1/tenants/{TEST_TENANT_ID}/edge/bundle",
            headers={"X-Admin-Master-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200
        manifest = resp.json()
        assert manifest["tenant_id"] == TEST_TENANT_ID
        assert "bundle_path" in manifest
        assert "checksum_sha256" in manifest

        # 2. Binary File Download endpoint
        dl_resp = client.post(
            f"/v1/tenants/{TEST_TENANT_ID}/edge/bundle?download=true",
            headers={"X-Admin-Master-Key": ADMIN_KEY},
        )
        assert dl_resp.status_code == 200
        assert "application/vnd.sqlite3" in dl_resp.headers["content-type"]
        assert "x-manifest-checksum" in dl_resp.headers
        content = dl_resp.content
        assert content[:16] == b"SQLite format 3\x00"

    try:
        os.unlink(temp_path)
    except OSError:
        pass


def test_tenant_edge_simulated_search_endpoint():
    mock_delta = EdgeSyncDelta(
        tenant_id=TEST_TENANT_ID,
        checkpoint_sequence=1,
        previous_sequence=0,
        added_chunks=[],
        added_vectors=[],
        deleted_chunk_ids=[],
        checksum_sha256="abcdef" * 10,
    )
    with patch.object(container.edge_sync_adapter, "get_delta_for_tenant", AsyncMock(return_value=mock_delta)):
        req = {
            "query": "architecture overview",
            "top_k": 3,
            "use_hybrid": True,
            "alpha": 0.5,
        }
        resp = client.post(
            f"/v1/tenants/{TEST_TENANT_ID}/edge/search",
            json=req,
            headers={"X-Admin-Master-Key": ADMIN_KEY},
        )
        assert resp.status_code == 200
        search_res = resp.json()
        assert "results" in search_res
        assert "latency_ms" in search_res
        assert "execution_tier" in search_res
