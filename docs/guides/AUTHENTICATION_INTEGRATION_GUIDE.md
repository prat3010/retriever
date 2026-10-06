---
id: Retriever_Auth_Integration_Guide
title: "Authentication & Identity Integration Guide: Adding Auth to Retriever"
category: guides
platform: retriever
tier: 4_api_gateway
status: authoritative
tags:
  - security/auth
  - architecture/hexagonal
  - identity/multi-tenant
  - api/fastapi
---

# Authentication & Identity Integration Guide: Adding Auth to Retriever

> **Authoritative guide on how authentication is structured in Retriever, how identity maps to multi-tenant Row-Level Security (RLS), and step-by-step instructions for adding new authentication providers and methods.**

---

## 1. Architectural Overview & Boundaries

Retriever follows strict **Hexagonal Architecture** (Ports and Adapters). Authentication is decoupled between domain contracts, inbound security dependencies, database persistence, and API routers:

```text
 ┌──────────────────────────────────────────────────────────┐
 │                      Client Invocations                  │
 │  (Browser UI, TypeScript SDK, REST Client, Micro-SaaS)   │
 └────────────────────────────┬─────────────────────────────┘
                              │ Bearer Token / API Key
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │  FastAPI Inbound Security Adapter                        │
 │  (src/adapters/api/security.py: get_current_user)        │
 ├────────────────────────────┬─────────────────────────────┤
 │ • Validates raw API Key    │ • Validates RS256 JWKS JWT  │
 │   via SHA-256 hash lookup  │   (Supabase / Custom OIDC)  │
 └────────────────────────────┴─────────────────────────────┘
                              │ Resolves
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │  Domain Identity Contract (Zero-Infrastructure)          │
 │  (src/domain/abstractions/identity.py: UserContext)      │
 │  tenant_id, user_id, roles: list[str], scopes: list[str]  │
 └────────────────────────────┬─────────────────────────────┘
                              │ Injects
                              ▼
 ┌──────────────────────────────────────────────────────────┐
 │  PostgreSQL Multi-Tenant Context (Row-Level Security)    │
 │  (src/adapters/database/connection.py: tenant_session)   │
 │  SET LOCAL app.current_tenant_id = :tenant_id            │
 └──────────────────────────────────────────────────────────┘
```

### Core Identity Model (`src/domain/abstractions/identity.py`)
In accordance with Hexagonal boundary constraints, the domain model does **not** import any database or HTTP libraries. It exposes pure Python data structures:

```python
@dataclass
class UserContext:
    tenant_id: str
    user_id: str
    roles: list[str] = field(default_factory=list)
    scopes: list[str] = field(default_factory=list)
    is_admin: bool = False
    rate_limit: int = 100
```

---

## 2. Existing Authentication Modes

Retriever natively supports two primary authentication modes today:

### Mode A: Tenant API Keys
- **Header**: `Authorization: Bearer ret_live_...` or `X-API-Key: ret_live_...`
- **Validation**:
  1. Key must start with the registered prefix (`ret_live_` or `ret_test_`).
  2. The server computes `SHA-256(raw_key)`.
  3. Constant-time database lookup against `api_keys.key_hash`.
  4. Returns `UserContext(tenant_id=..., user_id=..., roles=[api_key.role])`.

### Mode B: Asymmetric RS256 OIDC / Supabase JWTs
- **Header**: `Authorization: Bearer <supabase_or_oidc_jwt>`
- **Validation**:
  1. Fetches JWKS public keys from `SUPABASE_URL/auth/v1/.well-known/jwks.json` (or `OIDC_JWKS_URI`) with a 1-hour in-memory cache.
  2. Verifies cryptographic signature using RSA RS256.
  3. Verifies token expiration (`exp`), issuer (`iss`), and audience (`aud`).
  4. Resolves the external subject ID (`sub` or `email`) to an internal `UserDb` and `TenantDb`.
  5. Injects `UserContext` and scopes into request state.

---

## 3. Step-by-Step: How to Add a New Authentication Method

Whether adding **Clerk**, **Auth0**, **Firebase Auth**, **Custom JWTs**, or **mTLS/API Gateway Headers**, follow these 5 steps:

### Step 1: Update Configuration (`apps/api/src/config.py`)
Expose any required provider issuer URLs, JWKS endpoints, or audience secrets:

```python
class Settings(BaseSettings):
    # Existing settings...
    SUPABASE_URL: str = ""
    OIDC_JWKS_URI: str = ""
    OIDC_ISSUER_URL: str = ""
    OIDC_AUDIENCE: str = ""

    # New Provider Settings (e.g., Clerk or Auth0)
    CUSTOM_AUTH_PROVIDER_URL: str = ""
    CUSTOM_AUTH_JWKS_URI: str = ""
    CUSTOM_AUTH_AUDIENCE: str = ""
```

---

### Step 2: Implement the Token Verifier in Security Adapter (`apps/api/src/adapters/api/security.py`)

Add a helper function to verify tokens from your new provider. Use the existing cached JWKS client `_fetch_jwks_key`:

```python
async def _verify_custom_provider_jwt(token: str) -> dict:
    """Verify an asymmetric RS256 JWT issued by a third-party auth provider."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    if not kid:
        raise AuthenticationError("Token missing 'kid' in header.")

    jwk = await _fetch_jwks_key(settings.CUSTOM_AUTH_JWKS_URI, kid)
    if not jwk:
        raise AuthenticationError("Matching public key not found in JWKS.")

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=settings.CUSTOM_AUTH_AUDIENCE or None,
        issuer=settings.CUSTOM_AUTH_PROVIDER_URL or None,
        options={"verify_exp": True},
    )
    return claims
```

Hook it into `get_current_user` in `src/adapters/api/security.py`:

```python
async def get_current_user(
    request: Request,
    token: str | None = Security(api_key_header),
) -> UserContext:
    if hasattr(request.state, "user_context") and request.state.user_context:
        return request.state.user_context

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token.")

    clean_token = token[7:] if token.lower().startswith("bearer ") else token

    # 1. API Key Check
    if clean_token.startswith("ret_live_") or clean_token.startswith("ret_test_"):
        user_ctx = await identity_provider.validate_token(clean_token)
        request.state.user_context = user_ctx
        return user_ctx

    # 2. Custom Auth Provider Check
    if settings.CUSTOM_AUTH_JWKS_URI:
        try:
            claims = await _verify_custom_provider_jwt(clean_token)
            user_ctx = await identity_provider.resolve_or_provision_external_user(
                external_id=claims["sub"],
                email=claims.get("email", ""),
                name=claims.get("name", ""),
            )
            request.state.user_context = user_ctx
            return user_ctx
        except Exception as e:
            logger.debug(f"Custom provider validation failed, falling back: {e}")

    # 3. Supabase / OIDC Fallback
    # ...
```

---

### Step 3: Identity-to-Tenant Resolution & Auto-Provisioning (`src/adapters/database/identity_repository.py`)

When an external user logs in, they must map to a `TenantDb` and `UserDb` record in PostgreSQL. Add an auto-provisioning method to `SqlIdentityProvider`:

```python
async def resolve_or_provision_external_user(
    self, external_id: str, email: str, name: str
) -> UserContext:
    async with tenant_session(bypass_rls=True) as session:
        # Check if user exists
        stmt = select(UserDb).where(UserDb.external_id == external_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if user:
            return UserContext(
                tenant_id=str(user.tenant_id),
                user_id=str(user.user_id),
                roles=["member"],
                scopes=["document:read", "chat:read", "chat:write"],
            )

        # Auto-provision new Tenant & User on first login
        new_tenant_id = uuid.uuid4()
        new_user_id = uuid.uuid4()

        tenant = TenantDb(
            tenant_id=new_tenant_id,
            name=f"{name or email}'s Workspace",
            tier="starter",
            status="active",
        )
        session.add(tenant)

        new_user = UserDb(
            user_id=new_user_id,
            tenant_id=new_tenant_id,
            external_id=external_id,
            display_name=name or email,
            is_active=True,
        )
        session.add(new_user)
        await session.commit()

        return UserContext(
            tenant_id=str(new_tenant_id),
            user_id=str(new_user_id),
            roles=["owner"],
            scopes=["document:read", "document:write", "chat:read", "chat:write"],
        )
```

---

### Step 4: Protect Routes Using FastAPI Security Dependencies

To protect any route or router, declare `user_context: UserContext = Depends(get_current_user)`:

```python
from fastapi import APIRouter, Depends
from src.adapters.api.security import get_current_user
from src.domain.abstractions.identity import UserContext

router = APIRouter(prefix="/v1/documents", tags=["Documents"])

@router.get("/")
async def list_documents(user_context: UserContext = Depends(get_current_user)):
    # All database sessions automatically filter by user_context.tenant_id
    return {"tenant_id": user_context.tenant_id}
```

If role-based checks are needed (e.g. admin-only actions):

```python
from src.adapters.api.security import require_role

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user_context: UserContext = Depends(require_role(["owner", "admin"])),
):
    ...
```

---

### Step 5: Verify Multi-Tenant PostgreSQL RLS Context

Retriever enforces PostgreSQL Row-Level Security via `tenant_session(tenant_id)`.
Ensure that every database session used in downstream business logic sets the RLS session variable:

```python
async with tenant_session(tenant_id=user_context.tenant_id) as session:
    # All queries executed within this context are filtered by:
    # CREATE POLICY tenant_isolation_policy ON documents 
    # USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
    ...
```

---

## 4. Testing Your New Auth Implementation

Create an automated test in `apps/api/tests/unit/test_custom_auth.py`:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_unauthorized_without_token(client: AsyncClient):
    response = await client.get("/v1/auth/session")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_authorized_with_mock_jwt(client: AsyncClient, monkeypatch):
    # Mock JWKS verification to return valid test claims
    # Assert that /v1/auth/session returns 200 with matching tenantId
    ...
```

Run tests to ensure zero regressions:
```bash
pytest apps/api/tests/
```

---

## 5. Non-Negotiable Invariants

1. **Hexagonal Purity:** Never import FastAPI, SQLAlchemy, or JWT libraries into `src/domain/`.
2. **Tenant Isolation:** Never allow an unauthenticated or cross-tenant request to access database rows. All queries must run inside `tenant_session(tenant_id)` unless explicitly provisioning tenants with `bypass_rls=True`.
3. **Constant-Time Verification:** API key hashes must be computed with SHA-256 and compared in constant time (`secrets.compare_digest`).
4. **Never Log Raw Tokens:** Never output raw API keys or JWT tokens to logs or audit records. Only log tenant IDs, user UUIDs, or key prefixes.
