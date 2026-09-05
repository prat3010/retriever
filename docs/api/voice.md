---
id: Retriever_API_v1_voice
title: "API Specification: Sovereign Edge Voice & Whisper WebRTC (/v1/admin/voice, /v1/tenants/{tenantId}/voice)"
tier: 4_api_gateway
platform: retriever
tags:
  - api/voice
  - voice/webrtc
  - voice/whisper
  - platform/retriever
blast_radius: HIGH
security_auth: ADMIN_KEY_OR_BEARER_JWT
invariants:
  - "Raw end-user audio PCM bytes MUST NEVER egress to third-party public cloud APIs."
  - "Time-to-First-Audio-Byte (TTFAB) MUST be tracked and capped under 300ms SLA."
  - "Voice sessions and turn audio records MUST strictly enforce tenant_id isolation."
---

# API Specification: Sovereign Edge Voice & Local Whisper / WebRTC (`/v1/voice`)

#api #voice #webrtc #whisper #stt #tts #retriever

> **Authoritative REST and WebRTC signaling API specification for Sovereign Edge Voice, full-duplex WebRTC peer sessions, local Whisper speech recognition, and streaming neural speech synthesis (Platform Battery #20).**

---

## 1. Overview & Signaling Architecture

The Voice API enables natural, conversational voice interaction with zero cloud audio egress. Audio is processed on local host infrastructure using Whisper ASR and streaming neural TTS, communicating with browsers via WebRTC.

```text
  [ Client Browser / WebRTC Client ]                     [ Retriever Voice Router ]
                 │                                                   │
                 │ 1. POST /v1/tenants/{id}/voice/sessions           │
                 ├──────────────────────────────────────────────────►│ (Allocate VoiceSession)
                 │◄──────────────────────────────────────────────────┤
                 │    { "session_id": "vses_...", "sdp_offer": ... } │
                 │                                                   │
                 │ 2. POST /v1/tenants/{id}/voice/sessions/{id}/signal│
                 │    { "type": "answer", "sdp": "..." }             │
                 ├──────────────────────────────────────────────────►│
                 │                                                   │
                 │ 3. Full-Duplex WebRTC PeerConnection Established  │
                 │ ◄═══════════════════════════════════════════════► │
                 │   - User Audio Tracks (Opus / PCM16 @ 16kHz)      │
                 │   - Synthesized Speech Audio Stream (<250ms TTFAB)│
```

---

## 2. Admin Endpoints

### 2.1 Get Voice Telemetry
* **Endpoint:** `GET /v1/admin/voice/telemetry`
* **Auth:** `X-Admin-Master-Key: <ADMIN_MASTER_KEY>`
* **Description:** Retrieves real-time voice metrics across active sessions, total audio seconds processed, average turn-taking turnaround (TTT), and Time-to-First-Audio-Byte (TTFAB).
* **Response (200 OK):**
```json
{
  "active_sessions": 3,
  "total_sessions_today": 128,
  "total_audio_seconds_processed": 4820.5,
  "average_ttfab_ms": 218.4,
  "average_turn_latency_ms": 642.0,
  "stt_engine": "whisper_cpp_embedded",
  "active_battery": {
    "id": "sovereign_edge_voice",
    "name": "Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis",
    "status": "ACTIVE"
  }
}
```

---

## 3. Tenant Endpoints

### 3.1 Initialize Voice Session
* **Endpoint:** `POST /v1/tenants/{tenantId}/voice/sessions`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "user_id": "usr_client_executive",
  "sample_rate_hz": 16000,
  "channels": 1,
  "vad_sensitivity": 0.65,
  "selected_voice": "neural_natural",
  "audio_codec": "pcm16"
}
```
* **Response (201 Created):**
```json
{
  "session_id": "vses_9f86d081884c7d65",
  "tenant_id": "c7a8b9c0-1234-5678-90ab-cdef12345678",
  "created_at": "2026-09-05T18:00:00Z",
  "status": "INITIALIZED",
  "signaling_state": "HAVE_LOCAL_OFFER",
  "selected_voice": "neural_natural"
}
```

### 3.2 WebRTC Signal Exchange (SDP / ICE)
* **Endpoint:** `POST /v1/tenants/{tenantId}/voice/sessions/{sessionId}/signal`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "message_type": "candidate",
  "candidate": "candidate:842163049 1 udp 1677729535 192.168.1.14 54224 typ host ...",
  "sdp_mid": "0",
  "sdp_m_line_index": 0
}
```
* **Response (200 OK):** Confirms signaling message processing.

### 3.3 Transcribe Audio Chunk
* **Endpoint:** `POST /v1/tenants/{tenantId}/voice/sessions/{sessionId}/transcribe`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:**
```json
{
  "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
  "sample_rate_hz": 16000
}
```
* **Response (200 OK):**
```json
{
  "transcript": "Explain the zero-trust micro-enclave architecture.",
  "confidence": 0.96,
  "language": "en",
  "audio_duration_ms": 2400.0,
  "processing_time_ms": 142.5
}
```

### 3.4 Conversational Voice Turn (STT + RAG + TTS)
* **Endpoint:** `POST /v1/tenants/{tenantId}/voice/sessions/{sessionId}/turns`
* **Auth:** `Authorization: Bearer <JWT_OR_TENANT_KEY>`
* **Request Body:** Base64 audio chunk.
* **Response (200 OK):** Returns user transcript, grounded assistant text, synthesized audio PCM chunk, and latency metrics (`ttfab_ms`, `total_turn_ms`).
