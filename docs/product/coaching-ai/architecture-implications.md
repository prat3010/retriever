# Architecture Implications and Product Boundary

## Repository-derived capability map

| Existing Retriever capability | Coaching use | Fit | Product work still required |
|---|---|---|---|
| Tenant config, API keys, RLS, user-scoped chat | Isolate institute and end-user conversations. | Strong | App-owned authentication, roles, guardian relationships, consent, authorization. |
| Async ingestion, OCR/layout parsing, chunking, embeddings | Modules, notes, keys, later transcripts. | Strong for documents | Taxonomy, syllabus mapping, rights, media pipeline. |
| Hybrid search, metadata filters, reranking, MMR, query rewriting | Course/chapter-aware tutor/search. | Strong | Domain metadata contract and education retrieval evaluation corpus. |
| Citation validation and prompt templates | Evidence-linked teacher/institute style answers. | Strong | Citation UI, source policy, pedagogy/language handling. |
| GraphRAG | Retrieve concept/prerequisite/source relations. | Partial | Product-owned curriculum/attempt/mastery graph. |
| Structured extraction | Extract question/source attributes with review. | Partial | Human validation and item-bank lifecycle. |
| Guardrails, anonymization, encryption, retention, ACL | Protect learner/parent data/content. | Strong base | Consent, age assurance, minimization, purpose and product audit UX. |
| Evaluation, online tracing, feedback | Monitor tutor/generation quality. | Strong base | Education rubrics/gold sets and human review workflow. |
| Agentic engine, approvals, n8n | Future reviewable assistants/integrations. | Partial | Narrow tools, action approvals, idempotency, business rules. |

Sources: [constitution](../../constitution/master-vision.md), [architecture](../../architecture.md), [feature catalogue](../../RETRIEVER_FEATURE_CATALOG.md), and [roadmap](../../../ROADMAP.md).

## What remains Retriever core

- Reusable tenant-isolated ingestion, document lifecycle, local embeddings, retrieval/reranking, context assembly, citation validation, provider abstraction.
- Runtime config/prompts, quotas/costs, telemetry, evaluation primitives, auditability, encryption, PII/retention and generic chunk ACLs.
- Generic graph extraction/retrieval, structured extraction, safely scoped tools and approval primitives.
- Stable API/SDK contracts for client apps.

This follows Retriever’s explicit scope and anti-goals: it is a headless reusable engine, not a client UI, identity system, ERP, BI platform or workflow product.

## What belongs in the coaching application

- Student, guardian, faculty, counsellor, branch relationships; product RBAC and consent.
- Course, batch, calendar, syllabus, curriculum taxonomy, publishing, assessment, attempts, marks, attendance, homework, interventions, plans.
- Mastery interpretation, item-bank governance, analytics calculations, all role UX, CRM, ERP/fee operations, notifications and branch comparisons.
- Teaching policy: disclosure, hinting, escalation and approval rules.

**Boundary test:** if it must understand `student`, `batch`, `attempt`, `fee`, `guardian relationship`, or course pedagogy, it belongs outside Retriever unless it becomes a demonstrably multi-industry primitive.

## Conceptual data ownership — not a schema proposal

| Product domain | Records | Retriever interaction |
|---|---|---|
| Organization | institute, branch, programme, course, batch, calendar | Map institute to tenant and approved collections. |
| People/permissions | student, guardian link, teacher, roles, consent | App authenticates; derives Retriever identity/ACL context server-side. |
| Academic content | unit, concept, source, lecture, item, solution, rights/version | Ingest approved assets with course/chapter/version metadata/ACLs. |
| Learning evidence | assignment, attempt, score, feedback, attendance | Stays in product store; send only minimum context for a specific purpose. |
| Interventions | recommendation, review, task, outcome | Product workflow/audit; optional generic tools only after approval. |
| Operations | lead, enrolment, fee, payment, notice | Product/integration domain; never Retriever core data model. |

## Retrieval design implications

1. Controlled metadata: `course`, `exam`, `grade`, `subject`, `chapter`, `concept`, `source_type`, `version`, `language`, `audience`, `rights_status`, `teacher_approved`, `effective_from/to`.
2. Collections/ACLs separate student-ready material, faculty-only keys, parent notices and operator content; citations cannot become disclosure paths.
3. Question banks, solutions, and keys require separate access classes to stop active-assessment leakage.
4. Live score/attendance data remains in the product datastore and is supplied minimally with a clear purpose.
5. Product authorization constructs request context; free-text metadata/client-side role claims are never trusted.
6. Evaluate chapter attribution, key leakage, Hindi/Hinglish retrieval, OCR maths, citation access validity and stale sources before broad rollout.

## Privacy, security, multi-tenancy

India’s DPDP Act defines a child as under 18; its child-data provisions require verifiable parent/guardian consent and restrict detrimental processing, tracking/behavioural monitoring, and targeted advertising. [DPDP Act](https://www.indiacode.nic.in/bitstream/123456789/22037/1/a2023-22.pdf) and [Section 9](https://www.indiacode.nic.in/show-data?abv=CEN&actid=AC_CEN_45_0_00003_2023-22_1763464807080&orderno=9&sectionId=101275&sectionno=9&statehandle=123456789%2F1362)

- Minimize collection; use purpose-specific notices and durable consent/withdrawal records.
- Define age-appropriate parent/student visibility; do not expose private learning interactions by default.
- Do not use behavioural data for targeted advertising or infer sensitive traits.
- Make audio/image uploads opt-in, labelled, retention-limited and deletable.
- Test institute/branch/student/guardian/teacher cross-access end to end. Retriever RLS/ACL/encryption/purge are foundations, not complete product compliance.

## Evaluation and quality

| Surface | Pilot quality bar | Ongoing measure |
|---|---|---|
| Tutor | Correct sources, useful explanation, no key leakage, calibrated abstention. | Citation precision, faithfulness, pedagogy rubric, escalation, feedback. |
| Generated questions | Teacher-approved, solvable, correct key/rationale, blueprint coverage. | Approval/edit rate, errors, later difficulty/discrimination where reliable. |
| Lecture intelligence | Accurate transcript/timestamp for pilot content/language. | Sampled error, teacher correction rate. |
| Mastery/recommendation | Descriptive evidence before predictive labels. | Teacher agreement, action completion, outcomes, false-positive review. |
| Parent assistant | Accurate, authorized, plain language, sensitive escalation. | Escalations, corrections, auth-denials, complaints. |

Retriever’s faithfulness/relevance/context-recall metrics are necessary but insufficient; education needs pedagogical, learning, fairness and role-access evaluation.
