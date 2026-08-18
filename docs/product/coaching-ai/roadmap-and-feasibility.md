# Roadmap, Feasibility, Dependencies, and Risks

## Sequencing principle

Avoid a feature-heavy all-in-one start. Validate one high-trust learning loop with a design-partner institute and bounded subject/exam content. Expand only after quality, teacher adoption and privacy controls are proven.

| Phase | Goal | Candidate scope | Exit evidence | Deferred |
|---|---|---|---|---|
| 0 — Discovery | Validate pain/data access. | 10–15 role interviews, content/rights audit, workflow mapping. | Design partner, baseline, consent/rights plan. | Builds/integrations/migration. |
| 1 — Grounded pilot | Prove trusted value. | Curated library, cited text tutor, teacher review, simple practice/attempt capture, student/parent snapshots. | Quality threshold; teacher usefulness; no access incident. | Voice/image, predictions, ERP/CRM. |
| 2 — Assessment loop | Prove learning-loop utility. | Teacher-reviewed question drafts, blueprint, keys, attempt analysis, teacher-assigned remediation. | Item quality, teacher time saved, remediation signal. | Automatic publication/adaptive high-stakes tests. |
| 3 — Learning intelligence | Prove explainable personalization. | Curriculum graph, evidence views, plan drafts, lecture intelligence, reviewed intervention queue. | Teacher agreement/benefit; false-positive analysis. | Autonomous outreach/rank predictions/labels. |
| 4 — Operations | Win broader workflow. | CRM, payments/fees, timetable, attendance integrations, branch analytics. | Willingness to pay; integration reliability. | Bringing operational domains into Retriever. |
| 5 — Controlled agents | Safely reduce repetitive work. | Draft-only prep, parent support, intervention, admissions agents. | Permissions/audit/approval/rollback proof. | Autonomous external actions. |

## Feasibility

| Capability | Today | Main gap |
|---|---|---|
| Document-grounded text tutor | High | Curation, metadata, prompts/evaluations, client UI. |
| Teacher copilot drafts | High | Source governance and publishing review. |
| Basic question generation | Medium | Item schema, answer verification, duplicates/leakage, review. |
| Personalized practice | Medium | Attempt data and defensible concept taxonomy. |
| Lecture intelligence | Medium | Consent, transcription quality/cost, timestamps. |
| Image/handwritten doubts | Medium-low | OCR/math vision, language and privacy validation. |
| At-risk indicators | Medium-low | Historical data, fairness, action protocol, governance. |
| Mastery graph | Medium-low | Curriculum mapping, evidence quality, psychometrics. |
| ERP/CRM/branch analytics | Technically feasible | Large surface, entrenched competitors, commercial validation. |
| Autonomous agents | Low early | Permissions, tools, audit, approvals, reliability. |

## Dependencies

- Content rights/version governance for modules, solutions, recordings and student work.
- Clean course/batch/student IDs, syllabus taxonomy, answer keys, attendance source, timestamps.
- Separate client app/service for identity, consent, roles, academic records, UX, analytics/workflow.
- Golden questions per subject/language plus citation, rejection and abstention policies.
- Faculty owners for content, test approval, intervention review and parent escalation.
- LMS/ERP, payments, messaging and video integrations only where a validated workflow demands them.

## Risks and mitigations

| Risk | Mitigation before expansion |
|---|---|
| Wrong explanation / leaked key | Curated ACLs, citations, assessment-mode isolation, abstention, human review, red-team tests. |
| Stale/poor source | Versioned ownership/expiry, source-health dashboard. |
| Surveillance/harmful labels | Minimization, no punitive automation, explainability, consent, fairness review, human action. |
| Teacher adoption failure | Observe work, editable/exportable drafts, measure time saved and trust. |
| Commodity competition | Prioritize high-trust learning loop and institute-specific evidence. |
| Cost/latency | Quotas, caching, local embeddings, routing, batching, value-based limits. |
| Tenant/cross-role leakage | Product server policy plus Retriever RLS/ACL and end-to-end access testing. |

## Pilot scorecard

- Tutor: citation precision, grounded-answer acceptance, abstention appropriateness, time-to-help, reattempt/completion.
- Teacher: edit/approve rate, preparation time saved, confidence in evidence, active faculty.
- Learning: recommended-practice completion and comparable topic performance; do not claim causality without study design.
- Safety: access incidents, rights flags, unsafe responses, parent correction/escalation.
- Economics: AI/OCR/transcription cost per active learner, support workload, willingness to pay.
