# Enterprise Multi-Tenant Guide: Declarative Tenant Bundles

Retriever provides an enterprise-grade, declarative **Tenant Bundle** architecture. This pattern decouples proprietary business logic, specialized system prompt personas, domain-specific knowledge documents, and custom fallback behaviors from the core retrieval engine.

By adhering to this model, developers and organizations can customize, test, and deploy cognitive agents while ensuring **zero repository pollution** and **zero accidental data leakage** when working with open-source forks.

---

## 1. Architectural Philosophy

### Hexagonal Isolation & PostgreSQL Row-Level Security (RLS)
Retriever operates on Hexagonal Architecture (Ports and Adapters):
1. **The Core Engine** (`src/domain/`): Pure retrieval algorithms, late-interaction reranking (ColBERT MaxSim), reciprocal rank fusion (RRF), and dialectic consensus debate loops. It contains **zero** hardcoded tenant constants, corporate URLs, or bespoke fallbacks.
2. **The Database Layer**: Every document, chunk, vector embedding, and prompt template is bound to a `tenant_id` UUID. PostgreSQL Row-Level Security policies (`SET LOCAL app.current_tenant = ...`) strictly isolate tenant memory at the storage engine level.
3. **Tenant Bundles** (`data/tenants/<tenant_name>/`): The declarative configuration packs that define how a tenant behaves in the wild.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        Retriever Core Engine                           │
│  (HNSW Dense Search + BM25 Lexical + ColBERT Reranker + Swarm Quorum)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │ Dynamic Context Injection
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Declarative Tenant Bundle                         │
│  data/tenants/<bundle_name>/                                           │
│  ├── tenant.json           (UUID, Model, Hyperparameters, Fallbacks)   │
│  └── documents/            (Markdown / Text Knowledge Corpus)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               PostgreSQL Database Isolation (pgvector)                 │
│  tenants  |  prompt_templates  |  documents  |  document_chunks        │
│                [Enforced via Row-Level Security (RLS)]                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Git Privacy Boundary

Open-source contributors often need to run custom or private corporate data locally while maintaining an upstream fork.

To prevent private corporate dossiers or customer data from accidentally being committed:
- `data/tenants/.gitignore` ignores **all** folders in `data/tenants/` except `demo/` and documentation.
- The root `.gitignore` enforces this rule across Git trees.
- The `demo/` bundle serves as the canonical open-source template.

```gitignore
# data/tenants/.gitignore
*
!.gitignore
!README.md
!demo/
!demo/**
```

> [!TIP]
> You can create any number of tenant bundles on your local machine or staging VPS (e.g., `data/tenants/my_company/`, `data/tenants/customer_alpha/`). They will automatically be ignored by Git and will never appear in `git status` or pull requests.

---

## 3. Bundle Anatomy & Specification

A valid Tenant Bundle is a directory containing a `tenant.json` manifest and an optional `documents/` directory.

### Directory Layout

```text
data/tenants/demo/
├── tenant.json
└── documents/
    ├── 01_system_overview.md
    └── 02_api_standards.md
```

### Manifest Schema (`tenant.json`)

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "Demo Tenant — Acme Systems",
  "tier": "enterprise",
  "system_prompt": "You are a helpful, precise engineering assistant for Acme Systems. Ground your answers strictly in the provided documentation.",
  "active_model": "gemini-2.5-flash",
  "temperature": 0.4,
  "max_tokens": 2048,
  "fallbacks": {
    "engine_error": "⚠️ [Engine Notice] The cognitive service is currently experiencing high load. Please retry in a moment.",
    "no_context_found": "No verified records were found for that query in the Acme Systems knowledge base."
  }
}
```

### Configuration Attributes

| Property | Type | Description |
| :--- | :--- | :--- |
| `tenant_id` | `string` (UUID) | The primary key used across PostgreSQL tables for RLS scoping. |
| `name` | `string` | Display name of the tenant workspace in the Admin Studio (`apps/web`). |
| `tier` | `string` | Quota tier: `developer` (60 rpm), `production` (1,200 rpm), or `enterprise` (custom). |
| `system_prompt`| `string` | Grounding directive, behavioral tone, and persona instructions. |
| `active_model` | `string` | LLM model identifier (e.g. `gemini-2.5-flash`, `gpt-4o`, `ollama/qwen2.5`). |
| `temperature`  | `number` | Sampling temperature (`0.0` for deterministic logic, `0.7` for creative synthesis). |
| `max_tokens`   | `integer`| Maximum tokens generated in completion responses. |
| `fallbacks`    | `object` | Localized string messages emitted during engine errors or empty context retrieval. |

---

## 4. Provisioning & Ingestion Workflows

Retriever includes the `scripts/sync_tenant_bundle.py` CLI utility for synchronizing tenant bundles.

### 4.1. Offline Validation (Dry-Run)
Before writing to the database or network, run a dry-run to validate the manifest schema, verify UUID integrity, and inspect file chunking counts:

```bash
# Validate a specific bundle
python3 scripts/sync_tenant_bundle.py data/tenants/demo --dry-run

# Discover and validate all local bundles (including private ones)
python3 scripts/sync_tenant_bundle.py --all --dry-run
```

Output:
```text
🚀 Retriever — Declarative Tenant Bundle Provisioner
Targeting 1 bundle(s)... Mode: DRY-RUN

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 Tenant Bundle: demo
   Path: data/tenants/demo
   • Tenant ID:     00000000-0000-0000-0000-000000000001
   • Tenant Name:   Demo Tenant — Acme Systems
   • Active Model:  gemini-2.5-flash
   • System Prompt: 249 chars (preview: 'You are a helpful, precise engineering assistant for Acme Sy...')
   • Fallbacks:     2 configured (engine_error, no_context_found)
   • Documents:     2 found (2,499 bytes total)
       - 01_system_overview.md (1.3 KB)
       - 02_api_standards.md (1.2 KB)
   ✓ Validation Successful (DRY-RUN mode, no changes written).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ All tenant bundles verified and processed successfully.
```

### 4.2. Ingestion via HTTP API
Deploying against a running Retriever instance (local Docker or remote cloud VPS):

```bash
python3 scripts/sync_tenant_bundle.py data/tenants/demo \
  --api-url http://localhost:8000 \
  --api-key ret_live_demo_00000000000000000000000000000000
```

### 4.3. Direct Database Ingestion (High-Speed pgvector Bulk Load)
For high-performance offline bulk ingestion using Apple Silicon GPU or NVIDIA CUDA embeddings:

```bash
DATABASE_URL="postgresql://retriever:secret@localhost:5432/retriever" \
python3 scripts/sync_tenant_bundle.py data/tenants/demo --direct-db
```

This pipeline:
1. Upserts the tenant into `public.tenants`.
2. Stores the prompt template in `public.prompt_templates`.
3. Performs layout-aware chunking on all Markdown documents.
4. Generates dense 768-dim embeddings via local Ollama (`nomic-embed-text`).
5. Commits `documents`, `document_chunks`, and `vector_records` in a single atomic transaction.

---

## 5. Runtime Resolution & Fallback Behavior

When a client application queries `/v1/chat/completions`:

1. **Authentication**: The request's API key resolves the authenticated `tenant_id`.
2. **Prompt Synthesis**: `PromptBuilder` queries `PromptTemplateRegistry` for the tenant's registered system prompt template.
3. **Hybrid Context Retrieval**: Relevant chunks are retrieved via HNSW + BM25 reciprocal rank fusion.
4. **Fallback Handling**:
   - If no relevant context passes the semantic score threshold, the engine returns the tenant's configured `fallbacks.no_context_found`.
   - If an upstream inference provider encounters rate limits or connection drops, the engine returns `fallbacks.engine_error`.

---

## 6. Continuous Integration & Pre-Commit Verification

To verify that your tenant bundle manifests are well-formed in CI:

```yaml
# .github/workflows/verify_bundles.yml
name: Verify Tenant Bundles
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Validate Demo Tenant Bundle
        run: python3 scripts/sync_tenant_bundle.py data/tenants/demo --dry-run
```
