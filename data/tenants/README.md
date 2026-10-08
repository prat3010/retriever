# Declarative Tenant Bundles

Retriever implements a declarative **Tenant Bundle** architecture that keeps tenant configuration, custom persona prompts, knowledge documents, and localized fallback behaviors co-located in self-contained directories.

To preserve repository cleanliness and protect proprietary or personal data, **all tenant bundle directories inside `data/tenants/` (except `demo/`) are strictly gitignored by default**.

---

## Directory Structure

```text
data/tenants/
├── .gitignore                      # Ignores all directories except demo/ and documentation
├── README.md                       # This quickstart guide
│
├── demo/                           # Clean, fork-ready open-source demonstration bundle
│   ├── tenant.json                 # Manifest: identity, prompt, model settings & fallbacks
│   └── documents/                  # Knowledge base markdown files
│       ├── 01_system_overview.md
│       └── 02_api_standards.md
│
└── <your_custom_tenant>/           # 🔒 Gitignored automatically for privacy
    ├── tenant.json
    └── documents/
        └── *.md
```

---

## Manifest Specification (`tenant.json`)

Each tenant bundle requires a `tenant.json` manifest at its root:

```json
{
  "tenant_id": "00000000-0000-0000-0000-000000000001",
  "name": "Demo Tenant — Acme Systems",
  "tier": "enterprise",
  "system_prompt": "You are a helpful, precise engineering assistant for Acme Systems...",
  "active_model": "gemini-2.5-flash",
  "temperature": 0.4,
  "max_tokens": 2048,
  "fallbacks": {
    "engine_error": "⚠️ [Engine Notice] The cognitive service is experiencing high load.",
    "no_context_found": "No verified records were found for that query in the Acme knowledge base."
  }
}
```

### Fields

| Field | Type | Description |
| :--- | :--- | :--- |
| `tenant_id` | UUID string | Unique PostgreSQL tenant ID for Row-Level Security (RLS) scoping. |
| `name` | string | Human-readable tenant name displayed in the studio control plane. |
| `tier` | string | Service tier: `developer`, `production`, or `enterprise`. |
| `system_prompt` | string | Base persona instructions and grounding directives for chat answer synthesis. |
| `active_model` | string | Default LLM model identifier (e.g. `gemini-2.5-flash`, `gpt-4o`, `ollama/qwen2.5`). |
| `temperature` | float | Sampling temperature between `0.0` and `1.0`. Default is `0.4`. |
| `max_tokens` | integer | Max completion tokens to generate. Default is `2048`. |
| `fallbacks` | object | Localized fallback messages for runtime errors and out-of-context queries. |

---

## Quickstart: Creating a New Tenant Bundle

### 1. Copy the Demo Bundle
```bash
cp -r data/tenants/demo data/tenants/my_company_assistant
```

### 2. Configure Your Manifest
Edit `data/tenants/my_company_assistant/tenant.json`:
- Generate a new UUID (e.g., using `python3 -c "import uuid; print(uuid.uuid4())"`).
- Customize your assistant's `name` and `system_prompt`.
- Add custom fallback strings under `fallbacks`.

### 3. Add Knowledge Documents
Place your Markdown or text files in `data/tenants/my_company_assistant/documents/`:
```bash
cp ~/path/to/docs/*.md data/tenants/my_company_assistant/documents/
```

### 4. Ingest and Synchronize
Run the provisioning script to register the tenant and ingest the documents:
```bash
# Dry run to validate manifest and document parsing
python scripts/sync_tenant_bundle.py data/tenants/my_company_assistant --dry-run

# Execute full ingestion against your local or remote database
python scripts/sync_tenant_bundle.py data/tenants/my_company_assistant
```
