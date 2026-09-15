# Enterprise Identity Federation & Role-Based Vector Access Control (RB-VAC)

> **Platform Battery:** #34 (`enterprise_identity_federation`)  
> **Category:** `SAFETY_DEFENSE`  
> **Milestone:** M119 (`v1.9.0-alpha1`)  
> **Health Check Endpoint:** `GET /v1/identity/health`  

---

## 1. Architectural Overview

The **Enterprise Identity Federation & RB-VAC** engine bridges corporate Identity Providers (Okta, Azure AD / Microsoft Entra ID, Google Workspace, PingIdentity) with Retriever's cognitive memory layer:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   ENTERPRISE IDENTITY & SSO (SAML 2.0)                 │
│                                                                        │
│   Okta / Entra ID ──► XML Assertion ──► /v1/identity/saml/acs ──► JIT  │
│                       (X.509 Signed)    (Extract Badges)         Auth  │
├────────────────────────────────────────────────────────────────────────┤
│                 AUTOMATED DIRECTORY SYNC (SCIM 2.0 RFC 7644)           │
│                                                                        │
│   HR / IT Directory ──► REST Webhook ──► /v1/scim/v2/Users & /Groups   │
│   (New Hire / Term)     (Bearer Auth)    (Instant Deprovisioning)      │
├────────────────────────────────────────────────────────────────────────┤
│            ROLE-BASED VECTOR ACCESS CONTROL (RB-VAC) PRE-FILTERING     │
│                                                                        │
│   Employee Query Turn:                                                 │
│   1. Raw Candidate Retrieval (Top-K Chunks via Dense HNSW + BM25)      │
│   2. Set Intersection: (chunk.acl_groups ∩ user.security_groups) != ∅  │
│   3. Allowed Chunks ──► Passed to LLM prompt assembly                  │
│   4. Pruned Chunks  ──► Logged to RbVacPrunedTelemetry (Audit Chain)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Concepts

### 1. SAML 2.0 Single Sign-On
- **SP Metadata Generation:** Generates valid SAML Service Provider XML at `GET /v1/tenants/{tenantId}/identity/saml/metadata`.
- **Assertion Consumer Service (ACS):** Validates signed assertions at `POST /v1/tenants/{tenantId}/identity/saml/acs`, extracts `NameID`, session index, and maps attributes into corporate security groups (`engineering`, `finance`, `executive`).

### 2. SCIM 2.0 Directory Lifecycle (RFC 7643 / RFC 7644)
- **Bearer Authentication:** Scoped per-tenant via `POST /v1/tenants/{tenantId}/identity/scim/token`.
- **User Provisioning:** Create, retrieve, filter (`userName eq "..."`), and deactivate (`active = false`) users.
- **Group Membership Sync:** Synchronizes group definitions and members dynamically across identity changes.

### 3. Role-Based Vector Access Control (RB-VAC)
- **Pre-Retrieval Pre-Filtering:** Prevents unauthorized document text from ever reaching the prompt context window.
- **Mathematical Formula:**
  $$\text{Allowed}(c_i, u) \iff \left( * \in c_i.\text{acl\_groups} \right) \lor \left( c_i.\text{acl\_groups} \cap u.\text{security\_groups} \ne \emptyset \right)$$
- **Audit Logging:** Every pruned retrieval candidate is logged in structured compliance telemetry for SOC 2 and ISO 27001 auditing.

---

## 3. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/v1/identity/health` | Battery #34 operational status probe |
| `POST` | `/v1/tenants/{id}/identity/saml/config` | Configure tenant SAML IdP metadata |
| `GET` | `/v1/tenants/{id}/identity/saml/config` | Retrieve tenant SAML configuration |
| `GET` | `/v1/tenants/{id}/identity/saml/metadata` | Export Service Provider SAML XML metadata |
| `POST` | `/v1/tenants/{id}/identity/saml/acs` | SAML Assertion Consumer Service verification |
| `POST` | `/v1/tenants/{id}/identity/scim/token` | Generate/rotate SCIM 2.0 bearer token |
| `GET` | `/v1/scim/v2/ServiceProviderConfig` | RFC 7644 SCIM Service Provider configuration |
| `GET` | `/v1/scim/v2/Schemas` | RFC 7643 SCIM User & Group schemas |
| `GET` | `/v1/scim/v2/tenants/{id}/Users` | List directory users with filter and pagination |
| `POST` | `/v1/scim/v2/tenants/{id}/Users` | Provision a new user via SCIM |
| `GET` | `/v1/scim/v2/tenants/{id}/Users/{userId}` | Get user by ID |
| `PATCH` | `/v1/scim/v2/tenants/{id}/Users/{userId}` | Update user attributes or suspend |
| `DELETE` | `/v1/scim/v2/tenants/{id}/Users/{userId}` | Deprovision user |
| `GET` | `/v1/scim/v2/tenants/{id}/Groups` | List synchronized security groups |
| `POST` | `/v1/scim/v2/tenants/{id}/Groups` | Create a new security group |
| `GET` | `/v1/scim/v2/tenants/{id}/Groups/{groupId}` | Get security group details |
| `PATCH` | `/v1/scim/v2/tenants/{id}/Groups/{groupId}` | Add or remove group members |
| `DELETE` | `/v1/scim/v2/tenants/{id}/Groups/{groupId}` | Delete security group |
| `POST` | `/v1/tenants/{id}/identity/rbvac/simulate` | Test RB-VAC pre-filtering on candidate chunks |

---

## 4. Usage Examples

### Configure SAML 2.0 IdP
```bash
curl -X POST https://rag.prateeq.in/v1/tenants/tn_acme/identity/saml/config \
  -H "X-API-Key: ret_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "idp_entity_id": "https://idp.okta.com/exk_acme",
    "sso_url": "https://idp.okta.com/app/acme/sso/saml",
    "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n...\n-----END CERTIFICATE-----",
    "default_groups": ["all_staff"]
  }'
```

### Test RB-VAC Pre-Filtering
```bash
curl -X POST https://rag.prateeq.in/v1/tenants/tn_acme/identity/rbvac/simulate \
  -H "X-API-Key: ret_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "usr_intern",
    "email": "intern@acme.com",
    "security_groups": ["sales"]
  }'
```
