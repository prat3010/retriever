# ADR-006: Use Next.js for Web Reference Playground Application

## Status
Accepted

## Context
Retriever is a headless API platform, but requires a reference user interface to demonstrate features, manage configurations, and test grounding capabilities. This UI must support Server-Sent Events (SSE) token streaming and remain responsive across viewports.

## Problem
The reference frontend application must support:
1. High-fidelity UI styling conforming to our design guidelines (Outfit/Inter typography, dark/light modes, and micro-animations).
2. Clean integration with the backend SSE streaming endpoints.
3. Server-side rendering (SSR) and API routing to mask backend API credentials.
4. Quick setup and structured development for developers and AI agents.
5. Component responsiveness and keyboard accessibility (WCAG 2.1 compliance).

## Decision
Utilize **Next.js (App Router)** alongside **Vanilla CSS** and standard component libraries (e.g. Radix / shadcn primitives) for the web playground app.

## Alternatives Considered
* **Vanilla React (Vite):** A lightweight build tool, but lacks native API routing (making it harder to hide API keys without a separate proxy server) and requires manual configuration for server-side optimizations.
* **Vue (Nuxt.js) / Svelte (SvelteKit):** Excellent frameworks, but the team's familiarity with React and the extensive availability of accessible UI components (Radix / Tailwind/CSS primitives) favored React/Next.js.

## Consequences
* **Client Key Isolation:** Next.js Server Actions or API routes proxy client requests, ensuring API master keys are not exposed to the browser.
* **SSE Stream Processing:** Client hooks parse text streams on the fly, rendering text deltas with inline citations.
* **Standard Styling:** Implements design tokens using CSS variables, ensuring clean HSL slate scales and responsive structures.
* **Production Constraint:** The Next.js frontend MUST NOT query databases directly; all access must pass through the API gateway.

## Future Review Criteria
* Monitor client bundle sizes and rendering performance.
* Verify that Next.js client integrations continue to match OpenAPI contracts.
