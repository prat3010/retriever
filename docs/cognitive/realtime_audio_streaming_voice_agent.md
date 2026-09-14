# Real-Time Audio Streaming & Low-Latency Voice Agent Engine

**Architecture Document: Cognitive Subsystem (M114 / v1.4.0-alpha1)**  
**Protocol:** WebSocket Full-Duplex (PCM16 @ 16kHz Mono)  
**Boundary:** Hexagonal Domain (`src/domain/voice/voice_stream_service.py`)  

---

## 1. Subsystem Overview

The Real-Time Audio Streaming Voice Agent engine provides full-duplex conversational audio streaming with automatic speech endpointing and conversational barge-in.

### 1.1 Key Invariants
1. **Zero-Cloud Audio Egress:** Audio frames remain strictly in memory on sovereign infrastructure during processing.
2. **Sub-300ms TTFAB:** Streaming speech synthesis produces initial audio chunks before full turn generation completes.
3. **Conversational Barge-In:** Active generation tasks are cancelled immediately when the user interrupts by speaking.
4. **Hexagonal Purity:** `VoiceStreamService` contains no framework, database, or socket dependencies.

---

## 2. Component Structure

```text
apps/api/src/
├── domain/
│   ├── abstractions/
│   │   └── voice.py                  # Domain protocols, events, and message types
│   └── voice/
│       ├── voice_stream_service.py   # Pure stream lifecycle, VAD & barge-in logic
│       └── voice_orchestrator.py     # Turn history & high-level orchestration
├── adapters/
│   └── voice/
│       ├── whisper_transcription_adapter.py  # Local Whisper inference & RMS VAD
│       ├── speech_synthesis_adapter.py       # Neural TTS streaming chunks
│       └── webrtc_signaling_adapter.py       # WebRTC SDP/ICE exchange
└── routers/
    └── voice.py                      # FastAPI WebSocket endpoint (/stream/{sessionId})
```

---

## 3. Streaming Event Cycle

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Browser
    participant WS as WebSocket Router
    participant Service as VoiceStreamService
    participant VAD as Whisper VAD
    participant TTS as Neural TTS Streamer

    Client->>WS: Connect WebSocket (/stream/{sessionId}?token=...)
    WS->>Service: register_stream(sessionId)
    WS-->>Client: JSON session_ready (PCM16, 16kHz)
    
    loop Every 20ms
        Client->>WS: Binary PCM16 audio frame (640 bytes)
        WS->>Service: ingest_audio_frame(sessionId, frame)
        Service->>VAD: detect_voice_activity(frame)
        alt Speech Begins
            Service-->>WS: VAD_STATE (speech_detected)
            WS-->>Client: JSON vad_state
        else Silence Reaches 400ms Threshold
            Service-->>WS: VAD_STATE (endpoint_detected) + completed_audio
            WS-->>Client: JSON vad_state
            Note over WS,TTS: Launch background process_utterance task
            Service-->>WS: TRANSCRIPT_FINAL
            WS-->>Client: JSON transcript_final
            Service-->>WS: AGENT_THINKING
            WS-->>Client: JSON agent_thinking
            Service-->>WS: AGENT_TEXT_DELTA
            WS-->>Client: JSON agent_text_delta
            loop Audio Chunks
                Service->>TTS: stream_speech(agent_text)
                TTS-->>Service: chunk (PCM16)
                Service-->>WS: SynthesizedAudioChunk
                WS-->>Client: Binary audio bytes
            end
            Service-->>WS: TURN_COMPLETE
            WS-->>Client: JSON turn_complete
        end
        alt User Speaks During Agent Output (Barge-In)
            Note over Service: 3 consecutive speech frames detected
            Service->>Service: Cancel active utterance task
            Service-->>WS: INTERRUPTED (reason: "user_barge_in")
            WS-->>Client: JSON interrupted
            Note over Client: Client halts local audio playback
        end
    end
```

---

## 4. Benchmark & Latency Targets

- **Audio Frame Duration:** 20 ms (320 samples @ 16,000 Hz 16-bit).
- **VAD Processing Overhead:** < 0.2 ms per frame.
- **Whisper Edge ASR Latency:** 25–45 ms.
- **RAG Knowledge Retrieval:** 5–15 ms.
- **Time-to-First-Audio-Byte (TTFAB):** < 250 ms.
- **Barge-In Response Time:** < 60 ms (3 consecutive speech frames).
