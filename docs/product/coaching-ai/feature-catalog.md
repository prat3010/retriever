# Feature and Requirements Catalogue

## Catalogue convention

**MVP** is the smallest product worth validating with a design partner, not a build commitment. **Later** needs prior data/quality proof. **Optional** may matter commercially but is not central to the learning-loop thesis.

| Capability | Roles | Phase | Outcome / guardrail |
|---|---|---:|---|
| Content library and source governance | Admin, teacher | MVP | Approved material labelled by course, chapter, version, audience, and rights. |
| Cited AI tutor and doubt solver | Student, teacher | MVP | Text-first hints/explanations with sources, abstention and escalation. |
| Practice and teacher-authored tests | Student, teacher | MVP | Objective practice, review, attempts and feedback. |
| Teacher copilot | Teacher | MVP | Reviewable summaries, worksheets, quizzes and explanations; teacher publishes. |
| Student 360 profile | Student, teacher | MVP | Transparent attempts, attendance, work, teacher-set goals and evidence. |
| Parent update | Parent | MVP | Read-only attendance/test/next-event snapshot and reviewed weekly summary. |
| AI test generation | Teacher | Later | Retrieval-grounded question drafts with blueprint, verification and mandatory review. |
| Personalized remediation | Student, teacher | Later | Targeted practice based on validated concept evidence; override/opt-out. |
| Lecture intelligence | Student, teacher | Later | Transcript, timestamp search, summary and source-linked follow-up. |
| Study planner | Student, teacher | Later | Adaptable plan based on availability/milestones, not behavioural surveillance. |
| At-risk review queue | Teacher, admin | Later | Explainable review candidates; never a punitive automated action. |
| Knowledge graph/mastery | Student, teacher | Later | Explicit concepts, prerequisites, and evidence links. |
| Admissions CRM / ERP / fees | Admin, counsellor | Optional | Conventional operational product—integrate or build only after buyer discovery. |
| Multi-branch analytics | Owner, admin | Optional | De-identified cohort comparison and permission-limited drill-down. |
| Gamification | Student | Optional | Personal goals/streaks; no coercive public ranking by default. |
| Voice/image doubt intake | Student | Future | Consent-aware OCR/STT and verified science/maths quality. |
| Future agents | All | Future | Narrow tools, scoped permissions, review, audit and stop switch. |

## Role experiences

### Student: learn → practise → reflect → improve

- Ask a typed doubt within a selected course/chapter and choose `hint`, `explain`, or `show solution` mode.
- See source pages/lecture moments, submit attempts, and receive objective feedback or evidence-based error explanations.
- Follow a teacher-approved practice set/plan and see their own history plus a confidence-labelled mastery estimate.
- Flag an incorrect explanation and escalate to the teacher.

Do not promise universal visual/handwriting accuracy, real-time teacher impersonation, or exam-rank prediction.

### Teacher: prepare → teach → assess → intervene

- Curate source content, syllabus mappings, answer keys and tutor policy.
- Produce lesson recaps, flashcards, worksheet candidates, question blueprints and source-linked explanations; edit before use.
- Review individual/cohort evidence with freshness, confidence, and recommended action.
- Create intervention tasks; agents cannot contact parents, schedule work, or alter records without confirmation.

### Parent: understand → support → coordinate

- View consented attendance, test/event information, payments if owned by the product, notices and a simple learning summary.
- Ask bounded questions using only parent-permitted data; sensitive/ambiguous questions route to staff.
- Clearly see whether a message is AI-drafted or teacher-approved.

### Admin/owner: operate → monitor → improve

- Manage calendar, batches, content permissions, role mapping, retention and communication preferences.
- View aggregate service/content/quality/adoption signals and, later, CRM/fee/branch information.
- Compare branches on normalized cohorts with restricted drill-down.

## AI and RAG use cases

| Use case | Retrieval/model role | Required inputs | Quality gate |
|---|---|---|---|
| Tutor | Retrieve approved material; cite, answer, and ask diagnostic follow-up. | Curated content, course, language. | Citation correctness, pedagogy rubric, abstention. |
| Doubt solver | Match question to source/concept; provide progressive hints. | Text first; later image; exam/grade. | Answer verification, coverage, safety. |
| Test generator | Retrieve concepts/examples; produce blueprint-constrained item candidates. | Syllabus, mix, types, sources. | Teacher approval, key verification, duplicate/leakage check. |
| Personalized assessment | Select validated items; later safely generate. | Skill evidence, attempts, prerequisites. | Fairness/coverage, exposure controls, outcome measurement. |
| Lecture intelligence | Transcribe, segment, index, return timestamped results. | Recording, consent, metadata. | Transcription/timestamp quality, teacher review. |
| Teacher copilot | Summarize/draft from selected sources. | Approved materials, class context. | Traceability and teacher publish action. |
| Parent assistant | Retrieve parent-authorized facts. | Relationship proof, settings. | Authorization, plain language, human escalation. |
| At-risk support | Rank review candidates from explicit signals. | Attendance, completion, scores, freshness. | Bias/false-positive review, human confirmation. |

## Learning graph / personalization

```text
Course → syllabus unit → concept → prerequisite concept
             ↓                 ↓
     lecture / source ← question item ← attempt / mistake signal
                                         ↓
                                  teacher intervention
```

Each mastery estimate needs evidence count, time window, item/source lineage, confidence, and teacher override. Start with descriptive labels such as “needs more evidence,” not a falsely precise ability score.

## Future agents

- **Content curator:** flags duplicate/outdated/untagged materials and proposes taxonomy mapping.
- **Teacher prep agent:** prepares a review packet from specified sources and lesson plan.
- **Intervention coordinator:** drafts tasks/messages but never sends without confirmation.
- **Admissions assistant:** prioritizes/drafts follow-ups with counsellor approval and consent rules.
- **Parent support agent:** resolves narrow FAQs and escalates sensitive issues.
- **Operations anomaly assistant:** explains attendance/fee/engagement changes for operator review.
