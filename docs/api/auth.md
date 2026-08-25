---
id: Retriever_API_v1_auth
title: "API Specification: Authentication & Session Identity (/v1/auth)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/auth
  - security/jwks
  - security/rls
  - platform/retriever
blast_radius: CRITICAL
security_auth: BEARER_JWT
invariants:
  - "Every request must resolve to a valid tenant_id matching PostgreSQL RLS context."
  - "API keys must be stored strictly as SHA-256 hashes and checked in constant time."
---

# API Specification: Authentication & Session Identity (`/v1/auth`)

#api #auth #security #session #jwks #retriever

> **Authoritative specification for identity resolution, Supabase Auth RS256 JWKS validation, PKCE OAuth session tokens, and API key verification.**

---

## 1. Overview & Authentication Lifecycle

Retriever provides a unified multi-tenant authentication boundary supporting two primary authentication modes:
1. **API Key Authentication (`X-API-Key` / `Authorization: Bearer ret_live_...`):** High-entropy SHA-256 hashed API keys scoped to a specific tenant and role (`admin`, `client`, or `service_role`).
2. **Supabase Auth RS256 JWTs (`Authorization: Bearer <jwt>`):** Public-key verified asymmetric JWT tokens issued by Supabase Auth with JWKS signature validation and automatic tenant/user provisioning.

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client App / SDK
    participant Gateway as FastAPI Router (/v1/auth)
    participant AuthGuard as Security Dependency
    participant Supabase as Supabase JWKS Endpoint
    participant DB as PostgreSQL (RLS)

    Client->>Gateway: GET /v1/auth/session (Bearer Token / API Key)
    Gateway->>AuthGuard: get_current_user(token)
    alt Token starts with 'ret_live_'
        AuthGuard->>AuthGuard: Compute SHA-256(raw_key)
        AuthGuard->>DB: Query api_keys WHERE key_hash = :hash
        DB-->>AuthGuard: Return tenant_id, role, scopes
    else JWT Token
        AuthGuard->>Supabase: Fetch & Cache RS256 Public Key (JWKS)
        AuthGuard->>AuthGuard: Verify Signature, Issuer & Expiration
        AuthGuard->>DB: Resolve or Provision Tenant & User
        DB-->>AuthGuard: Return UserContext (tenant_id, user_id, roles)
    end
    AuthGuard-->>Gateway: Injected UserContext
    Gateway-->>Client: 200 OK (SessionContextResponse JSON)
```

---

## 2. API Endpoints

### 2.1 Get Active Session Context

Retrieve the authenticated tenant, user identity, roles, and granted permission scopes from the active Bearer token or API key.

- **HTTP Method:** `GET`
- **Path:** `/v1/auth/session`
- **Authentication:** `Bearer <API_KEY_OR_JWT>`
- **Response Model:** `SessionContextResponse`

#### Request Headers
| Header | Type | Required | Description |
|:---|:---|:---:|:---|
| `Authorization` | `string` | **Yes** | `Bearer ret_live_...` or Supabase RS256 JWT |
| `X-User-ID` | `string` | Optional | Client-scoped user UUID for ACL filtering |

#### Example Request (`curl`)
```bash
curl -X GET "https://rag.prateeq.in/v1/auth/session" \
  -H "Authorization: Bearer ret_live_a1b2c3d4e5f67890abcdef1234567890" \
  -H "Content-Type: application/json"
```

#### Example Request (TypeScript SDK)
```typescript
import { RetrieverClient } from "@retriever/client-js";

const client = new RetrieverClient({
  baseUrl: "https://rag.prateeq.in",
  apiKey: "ret_live_a1b2c3d4e5f6...",
});

const session = await client.getSession();
console.log("Tenant:", session.tenantId, "Roles:", session.roles);
```

#### Response Schema (`200 OK`)
```json
{
  "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09",
  "userId": "e8913bc1-7654-4321-9abc-1234567890ab",
  "roles": ["owner", "admin"],
  "scopes": [
    "document:read",
    "document:write",
    "chat:read",
    "chat:write",
    "search:read"
  ]
}
```

---

### 2.2 Google OIDC Token Exchange (Legacy)

> [!WARNING]
> This endpoint is maintained for backward compatibility. New frontends should authenticate directly against Supabase Auth PKCE and pass verified RS256 JWT tokens to Retriever.

- **HTTP Method:** `POST`
- **Path:** `/v1/auth/google`
- **Status:** `200 OK` (Legacy)
- **Request Body:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIs...",
  "email": "alex@example.com",
  "name": "Alex Developer"
}
```
- **Response Body (`200 OK`):**
```json
{
  "tenantId": "c9a28c30-e34d-4871-bc01-e9451d6c8b09",
  "userId": "e8913bc1-7654-4321-9abc-1234567890ab",
  "apiKey": "ret_live_a1b2c3d4e5f6...",
  "email": "alex@example.com",
  "name": "Alex Developer",
  "jwtToken": "eyJhbGciOiJIUzI1Ni...",
  "isNewTenant": false
}
```

---

## 3. Error Responses & Security Codes

### 3.1 Invalid Credentials (`401 Unauthorized`)
```json
{
  "error": "INVALID_CREDENTIALS",
  "detail": "API key hash not found or Supabase JWT signature expired.",
  "timestamp": "2026-08-25T05:35:00Z"
}
```

### 3.2 Tenant Isolation Breach (`403 Forbidden`)
```json
{
  "error": "TENANT_ISOLATION_BREACH",
  "detail": "Authenticated token does not hold permissions for tenant_id: 11111111-2222-3333-4444-555555555555",
  "timestamp": "2026-08-25T05:35:00Z"
}
```

---

## 🔗 Related Architecture & Cross-References
- [Master System Design](../implementation/system-design.md)
- [Database Schemas & pgvector](../infrastructure/database_and_schemas.md)
- [TypeScript Client SDK](../integrations/typescript_sdk.md)
- [Cloudflare Edge Proxy](../integrations/cloudflare_proxy_worker.md)
