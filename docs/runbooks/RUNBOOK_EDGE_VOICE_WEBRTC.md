# Operational Runbook: Sovereign Edge Voice Streaming & WebRTC Audio Pipelines

**Runbook ID:** RB-OPS-100  
**Audience:** Voice Systems Engineers, Audio Streaming Operators, SREs  
**Applies to:** Retriever AI Engine (v0.85.0+, Milestone 100)  
**Platform Battery:** Battery #20 (`edge_voice_stream`)  

---

## 1. System Overview & Audio Flow

The Sovereign Edge Voice pipeline delivers sub-300ms glass-to-ear voice conversational interactions through peer-to-peer WebRTC channels:
- **Speech-to-Text (STT):** Local quantized Whisper (`whisper-base.en` / `whisper-small`) running on edge CPU/GPU.
- **Voice Activity Detection (VAD):** Embedded Silero VAD filtering ambient silence and background noise.
- **Cognitive Interlock:** Low-latency streaming response from Retriever RAG or direct LLM.
- **Text-to-Speech (TTS):** Cartesia Sonic API or local Piper TTS streaming Opus audio packets over RTP.

```text
  [ Client Browser / Native App ]                             [ Retriever Voice Gateway ]
                 │                                                          │
                 │ 1. POST /v1/voice/session (SDP Offer)                    │
                 ├─────────────────────────────────────────────────────────►│
                 │◄─────────────────────────────────────────────────────────┤ (Returns SDP Answer)
                 │                                                          │
                 │ 2. Bidirectional WebRTC Media Stream (Opus @ 48kHz)      │
                 │ ════════════════════════════════════════════════════════ │
                 │ (Raw Audio Frames) ──► Silero VAD ──► Whisper STT        │
                 │                                         │                │
                 │                                         ▼                │
                 │ ◄── Audio Packets ◄── Cartesia TTS ◄── RAG Context       │
```

---

## 2. Health Monitoring & Observability Commands

### 2.1 Verify Voice Battery Status
Confirm that Battery #20 (`edge_voice_stream`) is operational:

```bash
curl -s -H "X-Admin-Master-Key: $ADMIN_MASTER_KEY" \
  https://rag.prateeq.in/v1/voice/health | jq .
```

**Expected Output:**
```json
{
  "status": "healthy",
  "battery_id": "edge_voice_stream",
  "whisper_model": "openai/whisper-base.en",
  "tts_provider": "cartesia",
  "active_webrtc_sessions": 3,
  "avg_roundtrip_latency_ms": 240.5,
  "vad_active_ratio": 0.32
}
```

---

## 3. Standard Operational Procedures (SOPs)

### SOP-VOICE-01: Initiating a WebRTC Voice Session

Clients exchange SDP parameters via the voice session endpoint:

```bash
curl -X POST "https://rag.prateeq.in/v1/voice/session" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "sdp_offer": "v=0\r\no=- 420 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n...",
    "voice_id": "sonic-english-conversational-01",
    "vad_threshold": 0.5,
    "temperature": 0.2
  }' | jq .
```

### SOP-VOICE-02: Testing Standalone Whisper Edge Transcription

Verify standalone audio transcription without full WebRTC initialization:

```bash
curl -X POST "https://rag.prateeq.in/v1/voice/transcribe" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@sample_query.wav" | jq .
```

### SOP-VOICE-03: Testing Cartesia Neural Audio Synthesis

Verify text-to-speech audio streaming:

```bash
curl -X POST "https://rag.prateeq.in/v1/voice/synthesize" \
  -H "Authorization: Bearer $TENANT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The Retriever platform is currently running with zero replication lag.",
    "voice_id": "sonic-english-conversational-01",
    "output_format": "mp3"
  }' --output test_speech.mp3
```

---

## 4. Incident Triage & Troubleshooting Matrix

| Incident Symptom | Probable Cause | Immediate Remediation |
| :--- | :--- | :--- |
| **ICE Connection Fails (`Failed to gather candidates`)** | NAT firewall blocking UDP ports 10000–20000; STUN server unreachable. | Verify STUN configuration (`stun:stun.l.google.com:19302`) and ensure coturn TURN relay is online. |
| **Audio Buffer Underrun / Stuttering** | Jitter buffer too small for erratic client Wi-Fi connection. | Increase `min_jitter_buffer_ms` from 50ms to 120ms in session negotiation configuration. |
| **Premature Speech Cutoff** | Silero VAD silence hangover window too short. | Increase `silence_hangover_ms` from 250ms to 450ms in `/v1/voice/session` payload. |
| **High End-to-End Latency (>600ms)** | Whisper running on CPU instead of GPU/Metal backend. | Verify `ctranslate2` or `whisper.cpp` accelerator detects CUDA / Metal compute devices. |

---

## 5. Automated Verification

Run voice pipeline automated unit and streaming integration tests:

```bash
pytest apps/api/tests/test_voice_streaming.py -v
```
