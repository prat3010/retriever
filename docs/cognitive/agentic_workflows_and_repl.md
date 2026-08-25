---
id: DeepDive_Agentic_Workflows_REPL
title: "Cognitive Deep-Dive: Autonomous Agentic Workflows & Sandboxed Python REPL"
tier: 6_retriever_cognitive
platform: retriever
tags:
  - cognitive/agentic
  - cognitive/react
  - cognitive/python-repl
  - platform/retriever
blast_radius: HIGH
invariants:
  - "Python REPL execution MUST run in an isolated subprocess sandbox with 2.0s CPU timeout."
  - "File system, socket networking, and subprocess creation MUST be disabled in REPL AST."
---

# Cognitive Deep-Dive: Autonomous Agentic Workflows & Sandboxed Python REPL

#cognitive #agentic #react #repl #sandbox #python #retriever

> **Technical architecture, tool execution loops, ReAct reasoning traces, and isolated Python REPL computation in Retriever.**

---

## 1. ReAct Execution Architecture

Retriever's agentic runtime implements the ReAct (Reason + Act) loop pattern with deterministic sandboxing:

```mermaid
flowchart TD
    UserGoal([User Goal / Analytical Prompt]) --> PromptBuilder[System Prompt + Tool Schema Definitions]
    
    subgraph Autonomous ReAct Loop
        PromptBuilder --> Reason[LLM Thought & Step Planning]
        Reason --> SelectTool{Select Action}
        
        SelectTool -->|Search| ToolSearch[Hybrid Search Tool Adapter]
        SelectTool -->|Math / Logic| ToolREPL[Sandboxed Python REPL]
        SelectTool -->|Graph| ToolGraph[GraphRAG Knowledge Traversal]
        SelectTool -->|Finish| Complete[Synthesize Final Response]
        
        ToolSearch & ToolREPL & ToolGraph --> Observe[Capture Observation & Output]
        Observe --> CheckIter{Iterations < MaxSteps?}
        CheckIter -->|Yes| Reason
        CheckIter -->|No (Limit)| Complete
    end
    
    Complete --> Output([Deliver Grounded Multi-Step Answer])
```

---

## 2. Hardened Python REPL Sandbox

The Python REPL adapter (`python_repl_calc`) provides 100% deterministic mathematical, statistical, and data-processing capabilities without risking host compromise:

```python
# Hardened AST Validator & Subprocess Sandbox
ALLOWED_BUILTINS = {"abs", "divmod", "max", "min", "pow", "round", "sum", "len", "print", "range"}
FORBIDDEN_AST_NODES = {
    ast.Import, ast.ImportFrom,  # No external imports
    ast.AsyncFor, ast.AsyncWith, # No async concurrency escapes
}
```

- **Execution Limits:** 2048ms CPU timeout, 64MB RAM memory cap, zero network sockets, zero disk writes.

---

## 🔗 Related Architecture & Cross-References
- [Agentic API Specification](../api/agentic.md)
- [RLM API Specification](../api/rlm.md)
- [Hybrid Search & Fusion](hybrid_search_and_fusion.md)
