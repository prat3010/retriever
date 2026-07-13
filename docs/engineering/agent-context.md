# AI Agent Context Guide: Token-Efficient Repository Execution

This guide defines how future AI coding agents must load context, read documentation, and implement code in the Retriever repository. Following this strategy minimizes token usage, prevents context window bloating, and ensures strict alignment with Retriever's architectural decisions.

---

## 1. Documentation Relevance Map

Before performing any code generation, modification, or research task, agents must reference the following documentation hierarchy:

```
                          [MANDATORY READING]
         (Read once at startup to establish supreme coding laws)
          ├── docs/constitution/master-vision.md
          ├── docs/architecture.md
          └── docs/engineering/engineering-playbook.md
                                 │
                                 ▼
                          [OPTIONAL REFERENCE]
         (Read selectively on demand when working on specific areas)
          ├── docs/features/core-platform.md  <── Read for feature specs
          ├── docs/implementation/system-design.md <── Read for database/API schema reference
          └── docs/decisions/ADR-*.md         <── Read for tech stack constraints
```

### 1.1 Mandatory Reading (The Platform Laws)
* **[master-vision.md](file:///Users/prateeksharma/Developer/retriever/docs/constitution/master-vision.md) (The Engineering Constitution):** Specifies the absolute coding manifesto, engineering hierarchy, RLS bypass bans, and non-negotiable rules.
* **[architecture.md](file:///Users/prateeksharma/Developer/retriever/docs/architecture.md) (Logical Architecture Plan):** Specifies bounded contexts, Ports & Adapters interfaces, dependency directions, and the Client Integration Model (§15).
* **[engineering-playbook.md](file:///Users/prateeksharma/Developer/retriever/docs/engineering/engineering-playbook.md) (Engineering Standards):** Specifies code style conventions, directory import rules, file limits, and testing strategies.

### 1.2 Optional Reference (The System Blueprint)
* **[core-platform.md](file:///Users/prateeksharma/Developer/retriever/docs/features/core-platform.md) (Feature Specifications):** Explains feature behaviors and user journeys. Reference only when implementing the specific features described.
* **[system-design.md](file:///Users/prateeksharma/Developer/retriever/docs/implementation/system-design.md) (Physical Specifications):** Contains endpoint schemas, table structures, and background worker payloads. Reference only for checking API signatures or table indexes.
* **ADR Directory (`docs/decisions/`):** Explains why technologies (FastAPI, Redis, pgvector, etc.) were selected. Reference to verify technical boundaries.

---

## 2. Context Isolation & Token Preservation

To avoid context exhaustion and ensure code correctness, agents must follow strict context limits:

* **Targeted File Reads:** Never load entire files containing hundreds of lines of code if you only need to inspect a single method. Use the `StartLine` and `EndLine` parameters in the file viewing tool to read only the lines of interest.
* **Ripgrep Filtering:** When searching the codebase with `grep_search`, always narrow the search scope using `Includes` glob patterns (e.g. `*.py` or `!**/tests/**`) to prevent parsing irrelevant files.
* **No Redundant Folder Scans:** Avoid listing directories repeatedly if the workspace tree has already been logged.
* **Respect Existing Architecture:** Do not redesign interfaces or suggest new tech stacks. If a task requires modifying an external interface, check the `adapters/` folder or read the relevant ADR before proposing changes.

---

## 3. Recommended Context-Loading Strategy

| Task Category | Primary Docs | Context Files to Load | Action Strategy |
|---|---|---|---|
| **Bug Fixes** | [engineering-playbook.md](file:///Users/prateeksharma/Developer/retriever/docs/engineering/engineering-playbook.md) | 1. Failing code block (slice layout)<br>2. Unit test file mapping the failure context | Locate stack trace file $\rightarrow$ Read failure lines + 20 lines padding $\rightarrow$ Verify behavior in tests $\rightarrow$ Fix. |
| **Feature Development** | [core-platform.md](file:///Users/prateeksharma/Developer/retriever/docs/features/core-platform.md)<br>[system-design.md](file:///Users/prateeksharma/Developer/retriever/docs/implementation/system-design.md) | 1. Target domain folder (`domain/`) <br>2. Target Ports folder (`domain/abstractions/`) | Read feature spec and API contract $\rightarrow$ Find active Ports $\rightarrow$ Write domain rules first $\rightarrow$ Implement adapter. |
| **Refactoring** | [engineering-playbook.md](file:///Users/prateeksharma/Developer/retriever/docs/engineering/engineering-playbook.md) | 1. Files to refactor<br>2. Import boundary declarations | Map package imports $\rightarrow$ Verify unit test coverage is 100% $\rightarrow$ Apply edits within 40-line function limits. |
| **Infrastructure Work** | ADRs (`docs/decisions/`) | 1. Target adapter file (`adapters/`) <br>2. Docker Compose / Dockerfile | Check ADR constraints $\rightarrow$ Implement adapter matching Port parameters $\rightarrow$ Configure Docker/K8s deployment variables. |
| **AI Pipeline Work** | [engineering-playbook.md](file:///Users/prateeksharma/Developer/retriever/docs/engineering/engineering-playbook.md) | 1. Prompt template DB config mapping<br>2. `domain/inference/` files | Verify prompt dynamic loading patterns $\rightarrow$ Check LLM model abstract interface $\rightarrow$ Write streaming token adapters. |
| **Admin API Work** | [master-vision.md](file:///Users/prateeksharma/Developer/retriever/docs/constitution/master-vision.md) §14.2<br>[ROADMAP.md](file:///Users/prateeksharma/Developer/retriever/ROADMAP.md) M9 | 1. `domain/abstractions/` (ports)<br>2. API key scoping in `security.py`<br>3. RLS policies in `connection.py` | Read constitution on user-level isolation $\rightarrow$ Add `user_id` to chat tables $\rightarrow$ Extend RLS $\rightarrow$ Build admin CRUD endpoints $\rightarrow$ Run `test_architecture.py` to verify no regression. |
| **Client Onboarding** | [architecture.md](file:///Users/prateeksharma/Developer/retriever/docs/architecture.md) §15<br>[master-vision.md](file:///Users/prateeksharma/Developer/retriever/docs/constitution/master-vision.md) §5.1 | 1. Tenant CRUD in admin API<br>2. API key generation endpoint<br>3. Prompt template seeding | Create tenant $\rightarrow$ Generate API key (admin or client scope) $\rightarrow$ Configure LLM key + model $\rightarrow$ Seed default prompt template $\rightarrow$ Provide frontend with `apiKey` + `tenantId`. |
| **Database Changes** | [system-design.md](file:///Users/prateeksharma/Developer/retriever/docs/implementation/system-design.md) | 1. Database adapter files<br>2. SQL migrations folder | Check schema mappings $\rightarrow$ Generate Alembic migration $\rightarrow$ Add corresponding RLS schema policies $\rightarrow$ Verify down migration. |

---

## 4. When to Ask Clarifying Questions

AI agents must stop and ask the user for clarification in the following scenarios:
1. **Conflicting Guidelines:** If a requirement in a feature ticket directly contradicts the Engineering Constitution or RLS safety policies.
2. **Missing Core Credentials:** If external provider configuration values (e.g. LLM API keys) are missing from system environments.
3. **Ambiguous Tenant Isolation Bounds:** If a proposed feature needs to share data across tenant partitions, violating isolation rules.
4. **Tool/Library Additions:** Before adding any third-party library to a lockfile, as this introduces dependency changes.
5. **Human-in-the-Loop Approval Policies:** If a user action flow requires validation hooks, but the approval wait duration or timeout bounds are unspecified.
