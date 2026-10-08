# Acme Systems — API Engineering Standards

## 1. Authentication & Security
- **API Keys**: All REST endpoints require authentication via Bearer token: `Authorization: Bearer <token>` or header `X-API-Key: <key>`.
- **Tenant Scope Enforcement**: The tenant identifier is cryptographically extracted from the API key hash or JWT claims; client-supplied tenant query parameters are strictly disregarded in security decisions.
- **Rate Limiting**: Tiered token-bucket rate limits:
  - Developer Tier: 60 requests/minute.
  - Production Tier: 1,200 requests/minute.
  - Enterprise Tier: Dedicated custom quota with bursting capability.

## 2. API Design Conventions
- **Data Exchange**: JSON payloads adhering to OpenAPI 3.1 specifications.
- **Idempotency**: All mutation operations (POST, PUT, DELETE) accept an optional `Idempotency-Key` header to prevent duplicate execution during network retries.
- **Error Payloads**: Standard RFC 7807 Problem Details format:
  ```json
  {
    "type": "https://api.acme.com/errors/quota-exceeded",
    "title": "Rate Limit Exceeded",
    "status": 429,
    "detail": "Tenant request volume exceeded the 1,200 rpm threshold.",
    "instance": "/v1/documents/ingest"
  }
  ```
