---
name: docs-synchronizer
description: Manages the Spec-First Architecture Blueprinting, Post-Milestone Knowledge Graph Synchronization, and Roadmap update lifecycle.
---

# Documentation & Architecture Synchronizer Skill (Retriever)

Keeps retriever roadmap statuses, API specifications, and project status markdowns synchronized with live code.

## Lifecycle Workflow

### Phase 1: Pre-Milestone Contract Blueprinting (Before Code)
1. Draft or review the target architecture node in `docs/architecture_nodes/` with:
   - `id`, `tier: 6_retriever_cognitive`, `platform: Retriever`, `auth_level`, `blast_radius`, `file_path`
   - `status: planned` (ensures agents recognize target contract without hallucinating that code exists)
   - Non-negotiable safety invariants and expected test suites
2. Query the Knowledge Graph pre-flight:
   ```bash
   python3 scripts/query_architecture.py --target <entity_or_api>
   ```

### Phase 2: Post-Milestone Graph & Roadmap Synchronization (After Code & Tests)
1. Update node status from `status: planned` → `status: production`.
2. Check off completed milestone items in `ROADMAP.md` / `PROJECT_STATUS.md`.
3. Capture new architectural lessons or framework quirks in `docs/LEARNINGS.md`.
4. Run the full synchronization toolchain:
   ```bash
   python3 ../Prateek_website/scripts/sync_graph_with_code.py
   ```

