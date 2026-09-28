# 0034. Tenant Master Prompt Engine & Central Governance Policy Lock

Date: 2026-09-28
Status: Accepted

## Context

Prior to this decision, prompt templates in Retriever were manageable solely via the cluster Admin API (`/v1/admin/prompts`) and the Admin Web Studio. In multi-tenant SaaS environments where organizations rent dedicated tenant workspaces, customers require self-service capabilities to customize their AI chatbot's personality, conversational tone, and domain constraints without requiring cluster administrator intervention.

However, completely unrestricted prompt editing introduces enterprise compliance vulnerabilities:
1. **Regulatory Disclaimers & Compliance Drift:** Financial, healthcare, and legal tenants often require mandatory disclaimer clauses that cannot be altered or removed by end users.
2. **Brand Safety & Guardrail Overwrites:** Enterprise administrators need to enforce core system guardrails across all tenant API integrations while preventing individual developers from stripping baseline safety rules.

## Decision

We introduced the **Tenant Master AI Persona Engine with Enterprise Governance Policy Lock**:
1. **Self-Service Tenant Endpoints**:
   - `GET /v1/tenants/{tenantId}/prompts/default`: Securely returns the tenant's master system prompt.
   - `PUT /v1/tenants/{tenantId}/prompts/default`: Permits tenant API keys to customize prompt instructions.
2. **Enterprise Policy Lockdown (`is_locked: bool`)**:
   - Added `is_locked` column to `prompt_templates` via Alembic migration `p1q2r3s4t5u6_add_is_locked_to_prompt_templates.py`.
   - When `is_locked == True`, `PUT /v1/tenants/{tenantId}/prompts/default` returns `HTTP 403 Forbidden` (`detail="Master system prompt is locked by cluster administrator policy."`).
3. **Centralized Administrative Authority**:
   - Cluster administrators retain exclusive authority via `/v1/admin/prompts` and the Admin Studio to toggle `isLocked` and update template contents regardless of lock state.
4. **Hexagonal & Multi-Tenancy Boundary Isolation**:
   - Maintained 100% purity of domain abstractions (`src/domain/abstractions/inference.py`).
   - Tenant isolation enforced strictly via `verify_tenant_isolation`.

## Consequences
- Tenants enjoy seamless self-service AI persona configuration via standard tenant API keys.
- Compliance and security officers gain verifiable policy lock enforcement preventing unauthorized prompt drift.
- Backward compatibility preserved across all existing admin prompt endpoints.
