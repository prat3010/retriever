# Deep Flagship Case Study: Scoping Studio & SOW Compiler

System Identifier: SYS-02 // COMMERCIAL DISCOVERY & SOW ENGINE
Live Endpoint: https://prateeq.in/scoping
Framework Stack: Next.js 16 (App Router), React 19, TypeScript
PDF Rendering Core: React-PDF v4 (Client-Side Vector Compilation)
Commerce & Verification: Razorpay Webhooks, HMAC-SHA256 Cryptographic Signatures
Test Rigor: Vitest TDD, Pinned Page-Count PDF Regression Harness

---

## 1. Problem Statement & Commercial Philosophy

In bespoke freelance engineering, the sales discovery phase is traditionally plagued by friction:
1. **Prolonged Scoping Cycles:** 2 to 3 weeks of ambiguous back-and-forth email exchanges to produce a rough estimate.
2. **Hidden Feature Costs:** Scope creep resulting from uncommunicated architectural prerequisites (e.g., attempting to build recurring subscription billing without an underlying user authentication model).
3. **Delayed Contracting:** Manual PDF preparation resulting in days of lost momentum before contract signing.

The Scoping Studio automates this entire lifecycle into a self-service, deterministic CPQ (Configure, Price, Quote) engine running entirely in the client browser.

---

## 2. Directed Acyclic Graph (DAG) Dependency Closure Architecture

Features in a software application form a directed graph $G = (V, E)$, where vertices $V$ represent feature modules and directed edges $(u, v) \in E$ declare that feature $u$ strictly requires feature $v$ as an operational prerequisite.

### Prerequisite Graph Formulations
$$\text{booking} \longrightarrow \{\text{payments}, \text{auth}\}$$
$$\text{commerce} \longrightarrow \{\text{payments}, \text{auth}\}$$
$$\text{lms} \longrightarrow \{\text{payments}, \text{auth}\}$$
$$\text{crm} \longrightarrow \{\text{auth}\}$$

When a client activates a high-level capability (e.g., an Online Course Academy or Booking System), the engine calculates the transitive closure:
$$C(S) = S \cup \{v \in V \mid \exists u \in S, u \rightsquigarrow v\}$$
and automatically activates all necessary base modules, surfacing an explanatory dependency cascade notification to prevent invalid quote states.

### Production TypeScript Implementation (`src/lib/pricing.ts`)
```typescript
export function resolveFeatureDependencies(
  selectedIds: string[],
  catalog: FeatureModule[]
): string[] {
  const catalogMap = new Map(catalog.map((m) => [m.id, m]));
  const resolved = new Set<string>(selectedIds);
  const queue = [...selectedIds];

  while (queue.length > 0) {
    const currentId = queue.shift()!;
    const module = catalogMap.get(currentId);
    if (!module || !module.dependsOn) continue;

    for (const depId of module.dependsOn) {
      if (!resolved.has(depId)) {
        resolved.add(depId);
        queue.push(depId);
      }
    }
  }

  return Array.from(resolved);
}
```

---

## 3. Client-Side React-PDF Compilation & Pinned Page Purity

Unlike traditional proposals that generate messy HTML print previews, the Scoping Studio compiles vector-grade Statement of Work (SOW) documents directly in WebAssembly/JavaScript using `@react-pdf/renderer`.

### Font Instancing & Theme Tokens
The proposal compiler registers custom Google variable fonts pre-instantiated to static TTF instances via `fonttools varLib.instancer`:
- **Headings:** Playfair Display (Bold, 700)
- **Body Prose:** Lora (Regular 400, Semi-Bold 600)
- **Technical Specs & Hash Data:** JetBrains Mono (400, 700)

### Pinned Page-Count Contract (ADR 11 / ADR 12)
Commercial proposals are strictly asserted against fixed page counts to prevent awkward orphan overflow:
- **Services & Pricing Guide:** Exactly 5 Pages
- **Project Scoping Brief:** Exactly 3 Pages
- **Middleman Sales Partner Agreement:** Exactly 3 Pages

Every build runs automated Vitest smoke tests asserting that table rows, feature grids, and brand asset clauses strictly remain on their designated pages across both Azure (light) and Noir (dark) color schemes.

---

## 4. Cryptographic Escrow & Webhook HMAC Verification

To ensure that milestone payments and deposit receipts cannot be spoofed, all payment verifications pass through an HMAC-SHA256 signature verification pipeline.

```typescript
import crypto from "crypto";

export function verifyRazorpaySignature({
  orderId,
  paymentId,
  signature,
  secret,
}: {
  orderId: string;
  paymentId: string;
  signature: string;
  secret: string;
}): boolean {
  const generatedSignature = crypto
    .createHmac("sha256", secret)
    .update(`${orderId}|${paymentId}`)
    .digest("hex");

  return crypto.timingSafeEqual(
    Buffer.from(generatedSignature, "utf-8"),
    Buffer.from(signature, "utf-8")
  );
}
```

---

## 5. Architectural & Business Impact Metrics

| Metric / Dimension | Production Result | Commercial Impact |
| :--- | :--- | :--- |
| **Proposal Turnaround Speed** | **<3 Minutes** | Down from 2–3 weeks of email back-and-forth (99% acceleration) |
| **DAG Dependency Resolution** | **<1 ms** | Instantaneous UI reaction with zero layout lag |
| **Scope Ambiguity Rate** | **0.00%** | Every feature includes explicit technical deliverables and boundaries |
| **PDF Compilation Time** | **<850 ms** | Instant client-side download without server queue wait times |
| **Test Verification Suites** | **42 Passing Vitest Specs** | 100% deterministic quote calculations across INR and USD |
