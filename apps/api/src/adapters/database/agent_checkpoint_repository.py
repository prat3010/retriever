"""SQLAlchemy-backed Agent Checkpoint Repository for LangGraph state persistence.

Implements StateCheckpointerProtocol with strict tenant_id isolation and RLS.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select

from src.adapters.database.connection import tenant_session
from src.adapters.database.models import AgentCheckpointDb
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.agentic.abstractions import (
    StateCheckpointerProtocol,
    ThreadCheckpoint,
)

logger = logging.getLogger(__name__)


class SqlAgentCheckpointRepository(StateCheckpointerProtocol):
    """PostgreSQL state checkpointer enforcing multi-tenant isolation."""

    def __init__(self) -> None:
        # In-memory fallback/fast-path cache keyed by f"{tenant_id}:{thread_id}"
        self._memory_cache: dict[str, list[ThreadCheckpoint]] = {}

    def _validate_tenant_id(self, tenant_id: str) -> uuid.UUID:
        """Validate UUID format to prevent SQL injection and cross-tenant leakage."""
        try:
            return uuid.UUID(str(tenant_id))
        except (ValueError, AttributeError) as err:
            raise TenantIsolationViolationError(
                f"Invalid tenant_id format '{tenant_id}': {err!s}"
            ) from err

    async def save_checkpoint(self, checkpoint: ThreadCheckpoint) -> None:
        """Persist a state checkpoint snapshot into database and local cache."""
        valid_tenant_uuid = self._validate_tenant_id(checkpoint.tenant_id)
        cache_key = f"{checkpoint.tenant_id}:{checkpoint.thread_id}"

        # 1. Update in-memory fast-path
        if cache_key not in self._memory_cache:
            self._memory_cache[cache_key] = []
        # Replace if existing checkpoint_id, else append
        existing_idx = next(
            (
                i
                for i, c in enumerate(self._memory_cache[cache_key])
                if c.checkpoint_id == checkpoint.checkpoint_id
            ),
            None,
        )
        if existing_idx is not None:
            self._memory_cache[cache_key][existing_idx] = checkpoint
        else:
            self._memory_cache[cache_key].append(checkpoint)

        # 2. Persist to PostgreSQL with RLS
        try:
            async with tenant_session(tenant_id=checkpoint.tenant_id) as session:
                stmt = select(AgentCheckpointDb).where(
                    AgentCheckpointDb.tenant_id == valid_tenant_uuid,
                    AgentCheckpointDb.checkpoint_id == checkpoint.checkpoint_id,
                )
                res = await session.execute(stmt)
                row = res.scalar_one_or_none()

                created_dt = datetime.fromtimestamp(checkpoint.created_at, tz=UTC)
                if row:
                    row.node_name = checkpoint.node_name
                    row.step_index = checkpoint.step_index
                    row.state_snapshot = checkpoint.state_snapshot
                    row.created_at = created_dt
                else:
                    new_row = AgentCheckpointDb(
                        checkpoint_id=checkpoint.checkpoint_id,
                        thread_id=checkpoint.thread_id,
                        tenant_id=valid_tenant_uuid,
                        node_name=checkpoint.node_name,
                        step_index=checkpoint.step_index,
                        state_snapshot=checkpoint.state_snapshot,
                        created_at=created_dt,
                    )
                    session.add(new_row)
                await session.flush()
        except Exception as err:
            logger.debug(
                f"Database save_checkpoint note ({err}). Cached in memory.",
                exc_info=False,
            )

    async def get_checkpoint(
        self, tenant_id: str, thread_id: str, checkpoint_id: str
    ) -> ThreadCheckpoint | None:
        """Fetch a specific checkpoint strictly verifying tenant_id isolation."""
        valid_tenant_uuid = self._validate_tenant_id(tenant_id)
        cache_key = f"{tenant_id}:{thread_id}"

        # 1. Check in-memory cache
        if cache_key in self._memory_cache:
            for c in self._memory_cache[cache_key]:
                if c.checkpoint_id == checkpoint_id and c.tenant_id == tenant_id:
                    return c

        # 2. Query database
        try:
            async with tenant_session(tenant_id=tenant_id) as session:
                stmt = select(AgentCheckpointDb).where(
                    AgentCheckpointDb.tenant_id == valid_tenant_uuid,
                    AgentCheckpointDb.thread_id == thread_id,
                    AgentCheckpointDb.checkpoint_id == checkpoint_id,
                )
                res = await session.execute(stmt)
                row = res.scalar_one_or_none()
                if row:
                    return ThreadCheckpoint(
                        checkpoint_id=row.checkpoint_id,
                        thread_id=row.thread_id,
                        tenant_id=str(row.tenant_id),
                        node_name=row.node_name,
                        step_index=row.step_index,
                        state_snapshot=row.state_snapshot,
                        created_at=row.created_at.timestamp(),
                    )
        except Exception as err:
            logger.debug(f"Database get_checkpoint note ({err})", exc_info=False)

        return None

    async def get_latest_checkpoint(
        self, tenant_id: str, thread_id: str
    ) -> ThreadCheckpoint | None:
        """Retrieve the most recent checkpoint for an active thread."""
        valid_tenant_uuid = self._validate_tenant_id(tenant_id)
        cache_key = f"{tenant_id}:{thread_id}"

        # Check memory cache
        if self._memory_cache.get(cache_key):
            return sorted(
                self._memory_cache[cache_key],
                key=lambda c: (c.step_index, c.created_at),
                reverse=True,
            )[0]

        try:
            async with tenant_session(tenant_id=tenant_id) as session:
                stmt = (
                    select(AgentCheckpointDb)
                    .where(
                        AgentCheckpointDb.tenant_id == valid_tenant_uuid,
                        AgentCheckpointDb.thread_id == thread_id,
                    )
                    .order_by(
                        AgentCheckpointDb.step_index.desc(),
                        AgentCheckpointDb.created_at.desc(),
                    )
                    .limit(1)
                )
                res = await session.execute(stmt)
                row = res.scalar_one_or_none()
                if row:
                    return ThreadCheckpoint(
                        checkpoint_id=row.checkpoint_id,
                        thread_id=row.thread_id,
                        tenant_id=str(row.tenant_id),
                        node_name=row.node_name,
                        step_index=row.step_index,
                        state_snapshot=row.state_snapshot,
                        created_at=row.created_at.timestamp(),
                    )
        except Exception as err:
            logger.debug(f"Database get_latest_checkpoint note ({err})", exc_info=False)

        return None

    async def list_thread_checkpoints(
        self, tenant_id: str, thread_id: str
    ) -> list[ThreadCheckpoint]:
        """List all checkpoints recorded for a thread, ordered chronologically."""
        valid_tenant_uuid = self._validate_tenant_id(tenant_id)
        cache_key = f"{tenant_id}:{thread_id}"

        # If present in memory cache, return sorted
        if self._memory_cache.get(cache_key):
            return sorted(
                self._memory_cache[cache_key],
                key=lambda c: (c.step_index, c.created_at),
            )

        try:
            async with tenant_session(tenant_id=tenant_id) as session:
                stmt = (
                    select(AgentCheckpointDb)
                    .where(
                        AgentCheckpointDb.tenant_id == valid_tenant_uuid,
                        AgentCheckpointDb.thread_id == thread_id,
                    )
                    .order_by(AgentCheckpointDb.step_index.asc())
                )
                res = await session.execute(stmt)
                rows = res.scalars().all()
                results = [
                    ThreadCheckpoint(
                        checkpoint_id=r.checkpoint_id,
                        thread_id=r.thread_id,
                        tenant_id=str(r.tenant_id),
                        node_name=r.node_name,
                        step_index=r.step_index,
                        state_snapshot=r.state_snapshot,
                        created_at=r.created_at.timestamp(),
                    )
                    for r in rows
                ]
                self._memory_cache[cache_key] = results
                return results
        except Exception as err:
            logger.debug(f"Database list_thread_checkpoints note ({err})", exc_info=False)
            return []

    async def rollback_to_checkpoint(
        self, tenant_id: str, thread_id: str, checkpoint_id: str, fork: bool = False
    ) -> ThreadCheckpoint:
        """Roll back thread to a prior checkpoint, optionally pruning future steps."""
        valid_tenant_uuid = self._validate_tenant_id(tenant_id)
        target = await self.get_checkpoint(
            tenant_id=tenant_id, thread_id=thread_id, checkpoint_id=checkpoint_id
        )
        if not target:
            raise ValueError(
                f"Checkpoint '{checkpoint_id}' not found for thread '{thread_id}' in tenant '{tenant_id}'."
            )

        cache_key = f"{tenant_id}:{thread_id}"
        if not fork:
            # Prune memory cache
            if cache_key in self._memory_cache:
                self._memory_cache[cache_key] = [
                    c
                    for c in self._memory_cache[cache_key]
                    if c.step_index <= target.step_index
                ]

            # Prune database future checkpoints
            try:
                async with tenant_session(tenant_id=tenant_id) as session:
                    stmt = delete(AgentCheckpointDb).where(
                        AgentCheckpointDb.tenant_id == valid_tenant_uuid,
                        AgentCheckpointDb.thread_id == thread_id,
                        AgentCheckpointDb.step_index > target.step_index,
                    )
                    await session.execute(stmt)
                    await session.flush()
            except Exception as err:
                logger.debug(f"Database rollback delete note ({err})", exc_info=False)

        return target
