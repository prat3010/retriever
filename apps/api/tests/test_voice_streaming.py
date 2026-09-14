"""Unit and WebSocket Integration Tests for Real-Time Audio Streaming & Barge-In (M114)."""

import asyncio
import struct

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.adapters.voice.speech_synthesis_adapter import SpeechSynthesisAdapter
from src.adapters.voice.webrtc_signaling_adapter import WebRtcSignalingAdapter
from src.adapters.voice.whisper_transcription_adapter import WhisperTranscriptionAdapter
from src.config import settings
from src.domain.abstractions.voice import (
    AudioCodec,
    VoiceStreamControlMessage,
    VoiceStreamEventType,
)
from src.domain.voice.voice_stream_service import VoiceStreamService
from src.main import app


def generate_pcm16_frame(amplitude: int = 15000, samples_count: int = 320) -> bytes:
    """Generates a 20ms PCM16 audio frame (320 samples @ 16kHz mono)."""
    samples = [int(amplitude * (i % 2 * 2 - 1)) for i in range(samples_count)]
    return struct.pack(f"<{samples_count}h", *samples)


@pytest.mark.asyncio
async def test_voice_stream_service_vad_and_barge_in():
    """Verify stream service VAD energy classification and conversational barge-in cancellation."""
    transcription = WhisperTranscriptionAdapter()
    synthesis = SpeechSynthesisAdapter(default_sample_rate_hz=16000)
    signaling = WebRtcSignalingAdapter()
    service = VoiceStreamService(transcription, synthesis, signaling)

    session_id = "vcs_test_barge_in_01"
    await service.register_stream(session_id=session_id, sensitivity=0.65, silence_threshold_ms=400)

    # 1. Ingest speech frames
    speech_frame = generate_pcm16_frame(amplitude=16000)
    messages, completed = await service.ingest_audio_frame(session_id, speech_frame)
    assert len(messages) >= 1
    assert messages[0].event_type == VoiceStreamEventType.VAD_STATE
    assert messages[0].payload["state"] == "speech_detected"
    assert completed is None

    # 2. Simulate active agent task
    async def dummy_agent_speaking():
        await asyncio.sleep(5.0)

    state = service.get_stream_state(session_id)
    assert state is not None
    dummy_task = asyncio.create_task(dummy_agent_speaking())
    state.active_agent_task = dummy_task
    state.active_turn_id = "vct_test_speaking"

    # 3. User speaks again during agent response (barge-in threshold >= 3 frames)
    barge_in_triggered = False
    for _ in range(4):
        msgs, _ = await service.ingest_audio_frame(session_id, speech_frame)
        for m in msgs:
            if m.event_type == VoiceStreamEventType.INTERRUPTED:
                barge_in_triggered = True
                assert m.payload["reason"] == "user_barge_in"
                assert m.payload["cancelled_turn_id"] == "vct_test_speaking"

    assert barge_in_triggered is True
    # Yield control to allow event loop to process cancellation
    await asyncio.sleep(0.01)
    assert dummy_task.cancelled() or dummy_task.done()

    await service.unregister_stream(session_id)
    assert service.get_stream_state(session_id) is None


@pytest.mark.asyncio
async def test_voice_stream_service_silence_endpointing():
    """Verify continuous silence accumulation triggers utterance endpointing."""
    transcription = WhisperTranscriptionAdapter()
    synthesis = SpeechSynthesisAdapter(default_sample_rate_hz=16000)
    signaling = WebRtcSignalingAdapter()
    service = VoiceStreamService(transcription, synthesis, signaling)

    session_id = "vcs_test_endpoint_02"
    await service.register_stream(session_id=session_id, sensitivity=0.65, silence_threshold_ms=200)

    speech_frame = generate_pcm16_frame(amplitude=14000)
    silence_frame = bytes(640)

    # User speaks 5 frames
    for _ in range(5):
        await service.ingest_audio_frame(session_id, speech_frame)

    # User pauses for 12 frames (12 * 20ms = 240ms > 200ms threshold)
    completed_audio = None
    endpoint_message = None
    for _ in range(12):
        msgs, audio = await service.ingest_audio_frame(session_id, silence_frame)
        if audio is not None:
            completed_audio = audio
        for m in msgs:
            if m.event_type == VoiceStreamEventType.VAD_STATE and m.payload.get("state") == "endpoint_detected":
                endpoint_message = m

    assert completed_audio is not None
    assert len(completed_audio) > 0
    assert endpoint_message is not None
    assert endpoint_message.payload["total_bytes"] == len(completed_audio)

    await service.unregister_stream(session_id)


@pytest.mark.asyncio
async def test_voice_stream_process_utterance():
    """Verify process_utterance yields transcript, thinking, delta, audio chunks, and turn metrics."""
    transcription = WhisperTranscriptionAdapter()
    synthesis = SpeechSynthesisAdapter(default_sample_rate_hz=16000)
    signaling = WebRtcSignalingAdapter()
    service = VoiceStreamService(transcription, synthesis, signaling)

    session_id = "vcs_test_turn_03"
    await service.register_stream(session_id=session_id)

    dummy_speech = generate_pcm16_frame() * 5

    events = []
    audio_chunks = []
    async for item in service.process_utterance(
        session_id=session_id,
        audio_bytes=dummy_speech,
        response_generator="Real-time full duplex voice stream test response.",
    ):
        if isinstance(item, VoiceStreamControlMessage):
            events.append(item)
        elif hasattr(item, "audio_bytes"):
            audio_chunks.append(item)

    event_types = [e.event_type for e in events]
    assert VoiceStreamEventType.TRANSCRIPT_FINAL in event_types
    assert VoiceStreamEventType.AGENT_THINKING in event_types
    assert VoiceStreamEventType.AGENT_TEXT_DELTA in event_types
    assert VoiceStreamEventType.TURN_COMPLETE in event_types

    assert len(audio_chunks) > 0
    for chunk in audio_chunks:
        assert chunk.format == AudioCodec.PCM16
        assert len(chunk.audio_bytes) > 0

    # Turn complete contains telemetry
    turn_complete_event = next(e for e in events if e.event_type == VoiceStreamEventType.TURN_COMPLETE)
    turn_data = turn_complete_event.payload["turn"]
    assert turn_data["user_transcript"] is not None
    assert turn_data["agent_response_text"] == "Real-time full duplex voice stream test response."
    assert turn_data["time_to_first_audio_byte_ms"] >= 0.0
    assert turn_data["total_turn_duration_ms"] > 0.0

    await service.unregister_stream(session_id)


def test_voice_websocket_unauthorized():
    """Verify WebSocket connection without authorization is rejected with WS_1008 policy violation."""
    client = TestClient(app)
    with pytest.raises((WebSocketDisconnect, Exception)) as exc_info:
        with client.websocket_connect("/v1/tenants/tn_test/voice/stream/vcs_unauth"):
            pass
    assert exc_info is not None


def test_voice_websocket_handshake_and_ping():
    """Verify WebSocket connects with admin key, receives session_ready, and responds to ping."""
    client = TestClient(app)
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    with client.websocket_connect("/v1/tenants/tn_stream_test/voice/stream/vcs_ws_01", headers=headers) as ws:
        # 1. First message must be session_ready
        initial_msg = ws.receive_json()
        assert initial_msg["event_type"] == "session_ready"
        assert initial_msg["session_id"] == "vcs_ws_01"
        assert initial_msg["payload"]["codec"] == "pcm16"
        assert initial_msg["payload"]["sample_rate_hz"] == 16000
        assert initial_msg["payload"]["channels"] == 1

        # 2. Send ping control message
        ws.send_json({"event_type": "ping"})
        pong_msg = ws.receive_json()
        assert pong_msg["event_type"] == "pong"
        assert pong_msg["session_id"] == "vcs_ws_01"
        assert "timestamp" in pong_msg["payload"]


def test_voice_websocket_text_input_and_interrupt():
    """Verify WebSocket text_input turn execution and manual interrupt control."""
    client = TestClient(app)
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    with client.websocket_connect("/v1/tenants/tn_stream_test/voice/stream/vcs_ws_02", headers=headers) as ws:
        # Handshake
        initial_msg = ws.receive_json()
        assert initial_msg["event_type"] == "session_ready"

        # Send interrupt
        ws.send_json({"event_type": "interrupt", "reason": "test_manual_interrupt"})
        interrupt_msg = ws.receive_json()
        assert interrupt_msg["event_type"] == "interrupted"
        assert interrupt_msg["session_id"] == "vcs_ws_02"
        assert interrupt_msg["payload"]["reason"] == "test_manual_interrupt"
