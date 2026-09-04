# ADR-014: DSPy Declarative Prompt Compilation & Algorithmic Self-Optimization

## Status
Accepted

## Context
Handcrafted string prompt templates (e.g. *"You are an expert lawyer... Answer carefully"*) are brittle, domain-inflexible, and degrade unpredictably when question distributions shift. When an enterprise tenant uploads unique domain documents, engineering teams are forced to spend manual hours tweaking prompt phrasing and cherry-picking few-shot examples.

## Problem
We need an automated, mathematically verifiable method to optimize system prompt instructions and discover high-leverage few-shot demonstrations directly from customer evaluation datasets.

## Decision
Adopt the **DSPy Declarative Programming Paradigm** with teleprompter optimization:
1. Define cognitive input/output interfaces as declarative contracts (`RAGAnswerSignature: (context, question) -> (thought, answer)`).
2. Implement `DSPyCompilerAdapter` providing `BootstrapFewShot` and `MIPROv2` teleprompters that filter and rank exemplars using composite grounding metrics.
3. Store compiled programs in PostgreSQL (`compiled_prompt_programs`) with 1-click atomic production hot-activation.
4. Integrate runtime injection directly into `PromptBuilder`, falling back to standard string templates when no compiled program is active.

## Consequences
* **Measurable Accuracy Lift:** Replaces guesswork with empirical metric optimization ($\Delta > 0$ score improvement required for activation).
* **Zero Inference Overhead:** Active programs are cached in memory; prompt injection adds 0ms database latency.
* **Compilation Compute:** Running teleprompter optimization passes requires multiple LLM calls over evaluation splits, scheduled as asynchronous administrative background jobs.

## Future Review Criteria
* Evaluate multi-signature DSPy compilation chains for multi-agent workflows.
