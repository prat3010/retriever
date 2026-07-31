---
name: retriever-retrospective
description: Conducts post-milestone retrospective audits to evaluate code diffs, capture architectural lessons, update ADRs, and refine workspace AGENTS.md rules.
---

# Retriever Retrospective & Continuous Learning Skill

This skill defines the post-implementation reflection protocol executed after completing milestones or major tasks in the Retriever platform.

## Post-Milestone Retrospective Protocol

Upon completing a milestone or feature, execute the following 4-step retrospective workflow:

### Step 1: Code Diff & Complexity Audit
- Review `git diff` to ensure no over-engineering, dead code, or redundant helper classes were added.
- Verify that Hexagonal Architecture boundaries remain intact (no infrastructure leaks in `src/domain/`).

### Step 2: Quality & Test Regression Review
- Run the full test suite (`pytest`) to confirm 100% pass rate.
- Identify any unexpected edge cases or performance bottlenecks that surfaced during implementation.

### Step 3: Architecture & Documentation Maintenance
- **Architectural Decision Records (ADRs):** If key architectural choices were introduced, document them under `docs/decisions/`.
- **Changelog & Status Updates:** Record completed milestone deliverables in `CHANGELOG.md` and update `PROJECT_STATUS.md` and `ROADMAP.md`.
- **Tech Debt Tracking:** Log any deferred technical debt in `TECH_DEBT.md` or mark resolved items as completed.

### Step 4: Workspace Memory & Rule Persistence
- If unexpected bugs, framework quirks, or domain constraints were discovered, update `.agents/AGENTS.md` with new workspace rules.
- This ensures future agent invocations automatically inherit these learnings and avoid repeating past mistakes.
