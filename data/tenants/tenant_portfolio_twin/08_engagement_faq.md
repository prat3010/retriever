# Recruiter, CTO & Technical Hiring Manager Engagement FAQ

Candidate Name: Prateek Sharma
Target Roles: Forward Deployed AI Engineer, Principal Systems Architect, Staff AI Engineer
Availability: Immediate / 2-Week Transition Sprint
Work Arrangement: 100% Remote (Operating Across US/EU/APAC Timezones)
Base Location: New Delhi, India
Current Working Rates: $40/hr, $300/day (Global/USD) | ₹3,000/hr, ₹20,000/day (Domestic/INR)
Notice Period: 0 Days (Independent Consultant / Forward Deployed)

---

## 1. Technical Depth & Architectural Decision-Making

### Q1: "Why choose local Ollama embeddings over cloud APIs like OpenAI text-embedding-3?"
**Answer:**
There are three critical enterprise considerations:
1. **Data Sovereignty & Compliance:** In healthcare, defense, and finance, sending raw proprietary documents or PII across third-party API boundaries violates GDPR, HIPAA, and SOC-2 data residency agreements. Running local Ollama instances on private VPS infrastructure guarantees that client data never leaves the security perimeter.
2. **Deterministic Latency & Zero Rate Limits:** Cloud embedding APIs are subject to external rate-limiting (HTTP 429), network jitter, and unpredictable regional outages. A local Ollama instance running `nomic-embed-text` delivers deterministic ~60ms embedding generation with zero external quota ceilings.
3. **Economics at Scale:** Ingesting 100,000 documents into OpenAI costs hundreds of dollars in API tokens. On an Oracle Cloud VPS, local embedding generation compute is 100% free ($0 incremental token cost), reducing operating expenditure by 90%+.

---

### Q2: "How do you guarantee zero cross-tenant data leakage in vector databases?"
**Answer:**
We reject application-level filtering as fundamentally unsound. In Retriever, multi-tenancy is enforced directly inside the PostgreSQL database engine kernel using Row-Level Security (RLS). 

When a client makes a request:
1. The authenticated tenant ID is extracted from the cryptographically verified JWT bearer token.
2. The database session checks out a connection and executes:
   `SET LOCAL app.current_tenant_id = :tenant_id;`
3. PostgreSQL evaluates the RLS policy `USING (tenant_id = current_setting('app.current_tenant_id')::uuid)`.

Even if an engineer writes a malformed query omitting the tenant filter, PostgreSQL physically blocks access to all rows belonging to other tenants at the storage engine layer.

---

### Q3: "How do you execute database schema migrations with zero downtime under active traffic?"
**Answer:**
We follow the **Expand and Contract pattern** paired with Alembic migrations and atomic symlink swapping:
1. **Phase 1 (Expand):** We introduce non-destructive schema changes (e.g., adding nullable columns, creating new tables or indexes concurrently via `CREATE INDEX CONCURRENTLY`). The existing application continues running uninterrupted.
2. **Phase 2 (Dual Write / Staging Boot):** The new version of the application is booted on a staging port (e.g. port 8001) pointing to the expanded schema. Automated readiness health probes (`/health/readiness`) run for 120 seconds to verify query performance.
3. **Phase 3 (Atomic Cutover):** Once health probes pass, Nginx atomically swaps traffic to the new release directory via an atomic symlink swap (`ln -sfn`).
4. **Phase 4 (Contract):** Once all old connections drain, a subsequent migration removes obsolete columns or tables without locking active transactions.

---

### Q4: "What is your philosophy on AI code generation and automated testing?"
**Answer:**
AI code generation without verification is technical liability. We apply the **Production Truth Doctrine**:
- AI agents are powerful for rapid drafting, but code is never merged without automated test execution (`pytest`, `vitest`).
- Tests must assert genuine boundary conditions: empty inputs, unicode edge cases, SQL injection attempts, and cryptographic HMAC mismatch attacks.
- We never weaken or mock out a test to make a pipeline look successful. If a test fails, that is authoritative signal that the underlying implementation has a regression.

---

### Q5: "What is the 'Ponytail Principle' and how does it prevent engineering bloat?"
**Answer:**
The Ponytail Principle channels the mindset of a seasoned systems architect who has witnessed systems collapse under unnecessary complexity. It demands:
1. Reach for the standard library before adding external npm or pip dependencies.
2. Choose native platform primitives (PostgreSQL RLS, CSS Modules, Vercel Edge caching) over bulky third-party SaaS wrappers.
3. Prefer deletion of dead code over the accumulation of speculative features.
4. Solve the real problem directly with the shortest, cleanest code possible.
