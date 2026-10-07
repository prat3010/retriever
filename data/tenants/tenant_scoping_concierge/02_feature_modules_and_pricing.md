# Modular Feature Add-Ons, Technical Specs & Pricing Matrix

Catalog Scope: Full Add-On Module Registry (18 Specialized Components)
Pricing Standard: Transparent Fixed-Price Pricing in INR (₹) and USD ($)
Prerequisite System: Directed Acyclic Graph (DAG) Dependency Enforced
Integration Standard: 100% Native Architecture Wiring (Zero Simulated Fakes)

---

## 1. Complete Modular Feature Catalog Table

| Module ID | Module Title | Category | Price (INR) | Price (USD) | Standard Turnaround | Direct Prerequisites (`dependsOn`) | Recommended Care Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `auth` | **User Auth & Client Portal** | Security / Auth | ₹25,000 | $350 USD | 3–5 Days | None | Standard Care |
| `payments` | **Payment Gateway Integration (Razorpay)** | Commerce | ₹45,000 | $600 USD | 4–6 Days | None | Standard Care |
| `cms` | **Headless Blog & CMS Content Management** | Content | ₹30,000 | $400 USD | 3–5 Days | None | Standard Care |
| `ai_rag` | **Private AI Knowledge Base / Vector Search** | Cognitive AI | ₹125,000 | $1,700 USD | 1–2 Weeks | None | Premium AI SLA |
| `ai_agents`| **Autonomous AI Agents & Workflows** | Cognitive AI | ₹135,000 | $1,800 USD | 1–2 Weeks | None | Premium AI SLA |
| `admin` | **Admin Dashboard & Role Access Control** | Operations | ₹75,000 | $1,000 USD | 5–8 Days | None | Standard Care |
| `email` | **Automated Transactional Emails (Resend)** | Marketing | ₹15,000 | $200 USD | 2–3 Days | None | Basic Care |
| `booking` | **Booking & Appointments Module** | Scheduling | ₹50,000 | $700 USD | 5–7 Days | `payments`, `auth` | Standard Care |
| `commerce`| **E-Commerce Storefront & Cart Module** | Commerce | ₹75,000 | $1,000 USD | 1–2 Weeks | `payments`, `auth` | Standard Care |
| `lms` | **LMS & Online Course Portal Module** | Education | ₹85,000 | $1,150 USD | 1–2 Weeks | `payments`, `auth` | Standard Care |
| `crm` | **CRM & Lead Management Module** | Operations | ₹60,000 | $800 USD | 5–8 Days | `auth` | Standard Care |
| `pwa` | **Progressive Web App (PWA) & Offline** | Mobile Web | ₹35,000 | $450 USD | 3–5 Days | None | Basic Care |
| `i18n` | **Multilingual & i18n Localization** | International | ₹30,000 | $400 USD | 3–5 Days | None | Basic Care |
| `integrations`| **Third-Party Integrations (Slack/Zapier)** | Automation | ₹40,000 | $550 USD | 3–5 Days | None | Standard Care |
| `video` | **Video Hosting & Streaming Module** | Media | ₹65,000 | $850 USD | 5–7 Days | None | Standard Care |
| `migration`| **Legacy Database & Data Migration** | Data Ops | ₹30,000 | $400 USD | 3–7 Days | None | Basic Care |
| `ai_voice_agent`| **Real-Time Voice AI Agent & WebRTC** | Voice AI | ₹95,000 | $1,250 USD | 1–2 Weeks | None | Premium AI SLA |
| `ai_vision_ocr` | **Multimodal AI Vision & OCR Engine** | Vision AI | ₹75,000 | $1,000 USD | 1–2 Weeks | None | Standard Care |

---

## 2. In-Depth Technical Specifications for High-Demand Modules

### A. Private AI Knowledge Base / Vector Search (RAG) (`ai_rag`)
- **Commercial Cost:** ₹125,000 INR / $1,700 USD
- **Layman Summary:** An intelligent AI assistant trained exclusively on your company's proprietary documents, manuals, and PDFs that answers questions 24/7 with verifiable citations.
- **Architectural Deliverables:**
  1. Multi-stage chunking pipeline supporting PDF, Markdown, and text with table atomicity and heading breadcrumbs.
  2. Local Ollama vector embeddings (`nomic-embed-text`) stored in PostgreSQL `pgvector` HNSW indexes.
  3. Hybrid fusion combining dense embeddings and sparse PostgreSQL BM25 full-text matching with Reciprocal Rank Fusion ($k=60$).
  4. Real-time Server-Sent Events (SSE) streaming chat completions with direct presigned source citation downloads.
  5. In-memory semantic query cache delivering sub-25ms repeat query responses.

### B. Autonomous AI Agents & Workflow Automation (`ai_agents`)
- **Commercial Cost:** ₹135,000 INR / $1,800 USD
- **Layman Summary:** Autonomous AI agents that execute multi-step operational workflows, search the web, interact with third-party APIs, and automate business tasks without human intervention.
- **Architectural Deliverables:**
  1. Multi-agent state graph orchestration using topological dependency execution.
  2. Structured tool calling with schema-validated input arguments and idempotent execution safeguards.
  3. Web scraping and automated data enrichment hooks.
  4. Webhook callback dispatching with retry queues and dead-letter failure logging.

### C. Real-Time Voice AI Agent & WebRTC Call Assistant (`ai_voice_agent`)
- **Commercial Cost:** ₹95,000 INR / $1,250 USD
- **Layman Summary:** A sub-second latency conversational voice AI widget embedded directly into your website or connected to phone numbers to handle customer inquiries and appointment scheduling.
- **Architectural Deliverables:**
  1. LiveKit WebRTC client-server audio streaming protocol.
  2. Deepgram streaming Speech-to-Text (STT) for near-instant speech transcription.
  3. ElevenLabs / OpenAI Realtime low-latency Text-to-Speech (TTS) synthesis.
  4. In-session function calling for calendar slot lookup and customer record updates.
  5. Structured call transcript storage and sentiment analysis telemetry.

### D. Multimodal AI Vision & Document Processing Engine (`ai_vision_ocr`)
- **Commercial Cost:** ₹75,000 INR / $1,000 USD
- **Layman Summary:** Automated document scanner powered by multimodal vision AI that extracts structured JSON data from receipts, invoices, identity cards, and complex scanned forms.
- **Architectural Deliverables:**
  1. Multimodal visual processing using Google Gemini Vision and Claude 3.5 Sonnet.
  2. Schema-constrained JSON extraction matching PostgreSQL database tables.
  3. Automated image preprocessing (contrast enhancement, deskewing, resolution scaling).
  4. Secure document storage integration via Supabase Storage with presigned download links.

### E. User Auth & Client Portal (`auth`)
- **Commercial Cost:** ₹25,000 INR / $350 USD
- **Layman Summary:** Secure customer login using Google accounts or passwordless email magic links leading into private personal account dashboards.
- **Architectural Deliverables:**
  1. Google OAuth 2.0 PKCE flow and passwordless magic link email dispatching.
  2. PostgreSQL Row-Level Security (RLS) policies guaranteeing strict tenant data privacy.
  3. Dual cookie and localStorage session persistence supporting Safari ITP.
  4. Secure user profile management and password reset flows.

### F. Payment Gateway Integration (`payments`)
- **Commercial Cost:** ₹45,000 INR / $600 USD
- **Layman Summary:** Seamless online checkout supporting Credit/Debit Cards, UPI, Netbanking, Apple Pay, and recurring monthly subscriptions.
- **Architectural Deliverables:**
  1. Razorpay Checkout modal with PCI-DSS compliant hosted payment processing.
  2. Automated webhook listeners validating HMAC-SHA256 cryptographic signatures.
  3. Idempotent payment ledger recording transactions, receipts, and order states.
  4. Automated PDF tax invoice generation with GST compliance.
