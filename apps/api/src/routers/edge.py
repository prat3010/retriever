"""FastAPI Router for Sovereign Edge SQLite & Vector Sync Engine (M98).

Exposes administrative observability and tenant-scoped endpoints for:
- Edge node registration and liveness heartbeats
- Differential sequence delta synchronization
- Standalone self-contained SQLite bundle generation and download
- Offline mutation reconciliation (Lamport timestamps / LWW)
- Sovereign edge hybrid search simulation
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.adapters.database.connection import tenant_session
from src.adapters.database.models import EdgeNodeDb, EdgeSyncCheckpointDb
from src.container import container
from src.domain.abstractions.edge_sync import (
    EdgeBundleManifest,
    EdgeMutation,
    EdgeNodeMetadata,
    EdgeNodeStatus,
    EdgeSearchRequest,
    EdgeSearchResponse,
    EdgeSyncConflictResolution,
    EdgeSyncDelta,
    OfflineExecutionTier,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/v1/admin/edge",
    tags=["edge", "admin"],
    dependencies=[Depends(verify_admin_key)],
)

tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/edge",
    tags=["edge", "sync"],
    dependencies=[Depends(verify_tenant_or_admin)],
)


class RegisterEdgeNodeRequest(BaseModel):
    """Payload to register an edge device or update its liveness heartbeat."""

    node_id: str = Field(..., min_length=2, max_length=128, description="Unique client machine/device ID")
    device_name: str = Field(..., min_length=1, max_length=255, description="Human-readable node alias")
    platform: str = Field(default="darwin_arm64", description="OS / architecture target")
    tier: OfflineExecutionTier = Field(
        default=OfflineExecutionTier.HYBRID_CACHE,
        description="Local edge capability tier",
    )
    client_version: str = Field(default="0.83.0", description="Retriever edge client SDK version")
    hardware_specs: dict[str, Any] = Field(default_factory=dict, description="RAM, CPU, vector storage capacity")


# ---------------------------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------------------------


@admin_router.get("/overview")
async def get_edge_overview() -> dict[str, Any]:
    """Provide system-wide overview of sovereign edge nodes and synchronization status."""
    try:
        async with tenant_session("00000000-0000-0000-0000-000000000000") as session:
            stmt = select(EdgeNodeDb).order_by(EdgeNodeDb.last_heartbeat_at.desc())
            res = await session.execute(stmt)
            nodes = list(res.scalars().all())

            total_nodes = len(nodes)
            now = datetime.now(UTC)
            online_count = 0
            platforms: dict[str, int] = {}
            tiers: dict[str, int] = {}

            node_list: list[dict[str, Any]] = []
            for n in nodes:
                is_active = (now - n.last_heartbeat_at).total_seconds() < 300
                if is_active:
                    online_count += 1

                plat = n.platform or "unknown"
                platforms[plat] = platforms.get(plat, 0) + 1

                tier_val = (n.meta_data or {}).get("tier", "hybrid_cache")
                tiers[tier_val] = tiers.get(tier_val, 0) + 1

                node_list.append(
                    {
                        "node_id": n.node_id,
                        "tenant_id": str(n.tenant_id),
                        "device_name": n.device_name,
                        "platform": n.platform,
                        "last_synced_seq": n.last_synced_seq,
                        "last_heartbeat_at": n.last_heartbeat_at.isoformat(),
                        "status": "online" if is_active else "offline",
                        "meta_data": n.meta_data,
                    }
                )

            res_ckpt = await session.execute(select(func.count(EdgeSyncCheckpointDb.checkpoint_id)))
            ckpt_count = res_ckpt.scalar() or 0

        battery = container.battery_service.get_battery("sovereign_edge_sync")

        return {
            "total_nodes": total_nodes,
            "online_nodes": online_count,
            "offline_nodes": total_nodes - online_count,
            "total_checkpoints": ckpt_count,
            "platforms": platforms,
            "tiers": tiers,
            "nodes": node_list[:50],
            "battery": battery.model_dump() if battery else None,
        }
    except Exception as e:
        logger.error(f"Failed to fetch edge overview: {e}", exc_info=True)
        return {
            "total_nodes": 0,
            "online_nodes": 0,
            "offline_nodes": 0,
            "total_checkpoints": 0,
            "platforms": {},
            "tiers": {},
            "nodes": [],
            "battery": None,
        }


# ---------------------------------------------------------------------------
# Tenant Endpoints
# ---------------------------------------------------------------------------


@tenant_router.get("/nodes", response_model=list[EdgeNodeMetadata])
async def list_tenant_edge_nodes(tenantId: str) -> list[EdgeNodeMetadata]:
    """List all registered edge nodes for the authenticated tenant."""
    t_uuid = uuid.UUID(tenantId)
    now = datetime.now(UTC)

    async with tenant_session(tenantId) as session:
        stmt = select(EdgeNodeDb).where(EdgeNodeDb.tenant_id == t_uuid).order_by(EdgeNodeDb.last_heartbeat_at.desc())
        res = await session.execute(stmt)
        records = list(res.scalars().all())

        results: list[EdgeNodeMetadata] = []
        for r in records:
            is_active = (now - r.last_heartbeat_at).total_seconds() < 300
            tier_val = OfflineExecutionTier(
                (r.meta_data or {}).get("tier", OfflineExecutionTier.HYBRID_CACHE.value)
            )
            results.append(
                EdgeNodeMetadata(
                    node_id=r.node_id,
                    tenant_id=str(r.tenant_id),
                    device_name=r.device_name,
                    platform=r.platform,
                    status=EdgeNodeStatus.ONLINE if is_active else EdgeNodeStatus.OFFLINE,
                    tier=tier_val,
                    last_synced_seq=r.last_synced_seq,
                    last_heartbeat_at=r.last_heartbeat_at.isoformat(),
                    vector_dimension=(r.meta_data or {}).get("vector_dimension", 768),
                    capabilities=(r.meta_data or {}).get("capabilities", ["fts5", "vector_blob"]),
                )
            )
        return results


@tenant_router.post("/nodes/register", response_model=EdgeNodeMetadata)
async def register_edge_node(tenantId: str, payload: RegisterEdgeNodeRequest) -> EdgeNodeMetadata:
    """Register or refresh heartbeat for an edge node device."""
    t_uuid = uuid.UUID(tenantId)
    now = datetime.now(UTC)

    async with tenant_session(tenantId) as session:
        node = await session.get(EdgeNodeDb, payload.node_id)
        if node:
            if node.tenant_id != t_uuid:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Node already registered under a different tenant.",
                )
            node.device_name = payload.device_name
            node.platform = payload.platform
            node.last_heartbeat_at = now
            node.status = "online"
            merged_meta = dict(node.meta_data or {})
            merged_meta.update(
                {
                    "tier": payload.tier.value,
                    "client_version": payload.client_version,
                    "hardware_specs": payload.hardware_specs,
                }
            )
            node.meta_data = merged_meta
            last_seq = node.last_synced_seq
        else:
            meta = {
                "tier": payload.tier.value,
                "client_version": payload.client_version,
                "hardware_specs": payload.hardware_specs,
                "vector_dimension": 768,
                "capabilities": ["fts5", "vector_blob", "reciprocal_rank_fusion"],
            }
            node = EdgeNodeDb(
                node_id=payload.node_id,
                tenant_id=t_uuid,
                device_name=payload.device_name,
                platform=payload.platform,
                last_synced_seq=0,
                last_heartbeat_at=now,
                status="online",
                meta_data=meta,
            )
            session.add(node)
            last_seq = 0

        await session.commit()

        return EdgeNodeMetadata(
            node_id=node.node_id,
            tenant_id=str(node.tenant_id),
            device_name=node.device_name,
            platform=node.platform,
            status=EdgeNodeStatus.ONLINE,
            tier=payload.tier,
            last_synced_seq=last_seq,
            last_heartbeat_at=now.isoformat(),
            vector_dimension=768,
            capabilities=["fts5", "vector_blob", "reciprocal_rank_fusion"],
        )


@tenant_router.get("/delta", response_model=EdgeSyncDelta)
async def get_edge_delta(
    tenantId: str,
    since_seq: int = Query(default=0, ge=0, description="Highest sequence number acknowledged by edge"),
    limit: int = Query(default=1000, ge=1, le=5000, description="Maximum chunks per batch"),
    node_id: str | None = Query(default=None, description="Optional requesting node ID to update checkpoint"),
) -> EdgeSyncDelta:
    """Fetch sequence delta changes since given sequence number for tenant."""
    delta = await container.edge_sync_adapter.get_delta_for_tenant(
        tenant_id=tenantId,
        since_seq=since_seq,
        limit=limit,
    )

    if node_id:
        t_uuid = uuid.UUID(tenantId)
        try:
            async with tenant_session(tenantId) as session:
                node = await session.get(EdgeNodeDb, node_id)
                if node and node.tenant_id == t_uuid:
                    node.last_synced_seq = max(node.last_synced_seq, delta.high_watermark_seq)
                    node.last_heartbeat_at = datetime.now(UTC)

                ckpt = EdgeSyncCheckpointDb(
                    tenant_id=t_uuid,
                    node_id=node_id,
                    sequence_num=delta.high_watermark_seq,
                    checksum_sha256=delta.checksum_sha256,
                )
                session.add(ckpt)
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not persist edge checkpoint: {e}")

    return delta


@tenant_router.post("/bundle")
async def generate_edge_bundle(
    tenantId: str,
    download: bool = Query(default=False, description="Stream .sqlite binary file directly if true"),
) -> Any:
    """Generate standalone self-contained SQLite edge database bundle."""
    try:
        manifest: EdgeBundleManifest = await container.edge_sync_adapter.create_standalone_bundle(tenant_id=tenantId)
        if download:
            headers = {
                "X-Manifest-Checksum": manifest.checksum_sha256,
                "X-Chunk-Count": str(manifest.total_chunks),
                "X-Vector-Dim": str(manifest.vector_dimension),
                "X-High-Watermark": str(manifest.checkpoint_sequence),
                "Content-Disposition": f'attachment; filename="retriever-edge-{tenantId[:8]}.sqlite"',
            }
            return FileResponse(
                path=manifest.bundle_path,
                filename=f"retriever-edge-{tenantId[:8]}.sqlite",
                media_type="application/vnd.sqlite3",
                headers=headers,
            )
        return manifest.model_dump()
    except Exception as e:
        logger.error(f"Failed to generate SQLite edge bundle for tenant {tenantId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Edge bundle compilation failed: {e}",
        ) from e


@tenant_router.post("/mutations", response_model=list[EdgeSyncConflictResolution])
async def reconcile_edge_mutations(
    tenantId: str,
    mutations: list[EdgeMutation],
) -> list[EdgeSyncConflictResolution]:
    """Ingest offline edge mutations (field notes, feedback) and reconcile into PostgreSQL."""
    try:
        return await container.edge_mutation_reconciler.reconcile_mutations(
            tenant_id=tenantId,
            mutations=mutations,
        )
    except Exception as e:
        logger.error(f"Failed to reconcile edge mutations for tenant {tenantId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mutation reconciliation failed: {e}",
        ) from e


@tenant_router.post("/search", response_model=EdgeSearchResponse)
async def simulated_edge_search(
    tenantId: str,
    request: EdgeSearchRequest,
) -> EdgeSearchResponse:
    """Simulate in-process Sovereign Edge SQLite search with FTS5 BM25 and vector fusion."""
    try:
        delta = await container.edge_sync_adapter.get_delta_for_tenant(tenant_id=tenantId, since_seq=0, limit=2000)
        engine = container.sqlite_edge_engine
        engine.initialize_schema()
        if delta.chunks:
            engine.apply_delta(delta)
        return engine.search(request)
    except Exception as e:
        logger.error(f"Simulated edge search failed for tenant {tenantId}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Edge search execution failed: {e}",
        ) from e
