"""Automated Quality Gate G3: Multi-Tenant Isolation & RLS Security Suite.

Tests strict tenancy boundaries, slug resolution, kill-switch key revocation,
and cross-tenant data isolation under Hexagonal Architecture.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.adapters.api.security import UserContext, verify_tenant_isolation
from src.domain.abstractions.exceptions import TenantIsolationViolationError


@pytest.mark.asyncio
async def test_tenant_isolation_matching_tenant() -> None:
    """Verify that requests to the authenticated tenant pass verification."""
    user_ctx = UserContext(
        user_id="usr-123",
        tenant_id="b0d64742-d5e9-425f-a6ca-57eb003cf2be",
        roles=["admin"],
        scopes=["admin:*"],
    )
    # Target matches authenticated tenant UUID
    await verify_tenant_isolation(
        tenantId="b0d64742-d5e9-425f-a6ca-57eb003cf2be",
        user_context=user_ctx,
        token="ret_live_test_valid_key",
    )


@pytest.mark.asyncio
async def test_tenant_isolation_slug_resolution() -> None:
    """Verify that slug paths resolve correctly to UUID for matching tenant."""
    user_ctx = UserContext(
        user_id="usr-123",
        tenant_id="b0d64742-d5e9-425f-a6ca-57eb003cf2be",
        roles=["admin"],
        scopes=["admin:*"],
    )
    # Target is known slug 'fin_audit' which maps to this UUID
    await verify_tenant_isolation(
        tenantId="fin_audit",
        user_context=user_ctx,
        token="ret_live_test_valid_key",
    )


@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_violation_triggers_kill_switch() -> None:
    """Verify that cross-tenant access raises TenantIsolationViolationError and revokes the rogue key."""
    user_ctx = UserContext(
        user_id="usr-attacker",
        tenant_id="a8f18df7-4ba3-4de9-9837-772a3d0ac582",  # red_team
        roles=["admin"],
        scopes=["admin:*"],
    )

    with patch("src.adapters.api.security.identity_provider.revoke_api_key_by_hash", new_callable=AsyncMock) as mock_revoke:
        with pytest.raises(TenantIsolationViolationError):
            await verify_tenant_isolation(
                tenantId="b0d64742-d5e9-425f-a6ca-57eb003cf2be",  # fin_audit
                user_context=user_ctx,
                token="ret_live_rogue_key_12345",
            )
        # Kill-switch assertion: API key must be immediately revoked by hash
        mock_revoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_tenant_isolation_cross_tenant_slug_spoofing() -> None:
    """Verify that slug spoofing against a different tenant is blocked and revoked."""
    user_ctx = UserContext(
        user_id="usr-attacker",
        tenant_id="a8f18df7-4ba3-4de9-9837-772a3d0ac582",  # red_team
        roles=["admin"],
        scopes=["admin:*"],
    )

    with patch("src.adapters.api.security.identity_provider.revoke_api_key_by_hash", new_callable=AsyncMock) as mock_revoke:
        with pytest.raises(TenantIsolationViolationError):
            await verify_tenant_isolation(
                tenantId="tech_docs",  # Maps to tech_docs UUID != red_team
                user_context=user_ctx,
                token="Bearer ret_live_rogue_key_67890",
            )
        mock_revoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_tenant_isolation_wildcard_admin_allowed() -> None:
    """Verify that system master key / wildcard context is permitted across tenants."""
    admin_ctx = UserContext(
        user_id="system-admin",
        tenant_id="*",
        roles=["admin"],
        scopes=["admin:*"],
    )
    # Should not raise for any tenant
    await verify_tenant_isolation(
        tenantId="b0d64742-d5e9-425f-a6ca-57eb003cf2be",
        user_context=admin_ctx,
    )
    await verify_tenant_isolation(
        tenantId="fin_audit",
        user_context=admin_ctx,
    )
