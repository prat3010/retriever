# Open Questions and Decision Log

## Provisional decisions

| ID | Decision | Status | Consequence |
|---|---|---|---|
| D-01 | Coaching Operating System is a separate client product; Retriever is its RAG platform. | Accepted for exploration | Preserves headless/reusable core and ERP/BI/workflow anti-goals. |
| D-02 | Start with curated, text-based, cited tutoring and teacher review. | Accepted | Best current Retriever fit and lower risk than image/voice/agents. |
| D-03 | Learner/operations records and mastery logic remain in coaching datastore. | Accepted | Domain-specific transactional/analytics concerns stay out of Retriever. |
| D-04 | Generated tests, consequential parent messages, and external actions require human review. | Accepted | Protects pedagogy, safety and trust. |
| D-05 | At-risk support is an explainable review queue, not a label or automatic action. | Accepted | Requires outcome/fairness validation. |
| D-06 | External web facts are visibly separated from institute-approved sources. | Accepted | Preserves provenance. |

## Questions before a design-partner pilot

### Customer and market

1. Which entry segment has urgent pain and usable content: JEE/NEET, UPSC, school tuition, certification, or skills?
2. Is the buyer seeking white-label student experience, faculty productivity, operational consolidation, or managed AI?
3. What existing system owns student, batch, attendance, test, payment and guardian data? Can it be integrated legally and reliably?
4. Which outcome supports purchase: teacher time, retention, parent support, conversion, or learning improvement?

### Pedagogy and content

5. Which syllabus/exam/languages are in scope? Is Hinglish expected and how is quality assessed?
6. Who owns/approves materials? What may be shown, quoted, transformed, or used to create items?
7. Which doubt policy applies: hints, worked steps, final answer after attempt, teacher escalation?
8. What is policy for active-test keys, plagiarism, teacher style, and sharing?
9. Can subject experts maintain a concept/prerequisite taxonomy and golden set?

### Data, safety, privacy

10. What ages are served, and how will guardian consent, withdrawal, and parent–student visibility work?
11. Which recommendation signals are permitted; which are prohibited (for example device/time-of-day activity)?
12. What retention, residency, deletion/export, breach response, vendor-sharing rules apply?
13. Who may access keys, faculty notes, chats, intervention history, and branch comparison data?
14. Is audio/video necessary initially; what consent and transcript retention policy is acceptable?

### Platform and delivery

15. What trusted backend asserts user/role/ACL context to Retriever? Devices must never self-declare privilege.
16. What collection/metadata/ACL convention separates course/chapter/version/audience and answer keys?
17. What provider, cost ceiling, latency SLO and fallback fit the pilot?
18. Which review process blocks release on citation, key leakage, authorization or pedagogical failure?
19. Standalone product, integration layer, or white-label template? This changes identity/data/support ownership.

## Revisit triggers

| Trigger | Revisit |
|---|---|
| Material is scans/handwriting/video | Prioritize OCR/transcription; defer tutor launch until sources are usable. |
| ERP replacement is required to win | Validate build-vs-integrate, but keep it outside Retriever. |
| Parent access conflicts with student privacy | Establish age/guardian visibility policy before summaries. |
| Low teacher editing on generated questions | Consider narrow auto-publish only after sustained validation and rollback. |
| Risk flags are biased/noisy | Disable ranking; revert to descriptive views and redesign with educators. |
