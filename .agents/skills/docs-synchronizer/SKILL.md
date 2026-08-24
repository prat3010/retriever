---
name: docs-synchronizer
description: Automatically scans modified Python files, updates ROADMAP.md, PROJECT_STATUS.md, CHANGELOG.md, and verifies cross-repo links.
---

# Documentation Synchronizer Skill (Retriever)

This skill keeps retriever roadmap statuses, API specifications, and project status markdowns synchronized with live code.

## Core Sync Rules

1. **Mandatory Documentation Audit**:
   - Whenever any code change is executed (even a minor bug fix or parameter tweak), the agent MUST audit all relevant project documentation (`ROADMAP.md`, `PROJECT_STATUS.md`, `CHANGELOG.md`, `ADMIN_DASHBOARD_GUIDE.md`, `docs/`) and update affected sections.

2. **Pre-Flight Inspection**:
   - Run `python3 scripts/query_architecture.py --target <component>` before modifying domain or router files to inspect cross-repo callers.

## Execution Command
```bash
python3 scripts/query_architecture.py --target all
```
