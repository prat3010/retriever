"""Unit and REST API Test Suite for Sovereign Edge Voice & WebRTC (M100)."""

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.voice.speech_synthesis_adapter import SpeechSynthesisAdapter
from src.adapters.voice.webrtc_signaling_adapter import WebRtcSignalingAdapter
from src.adapters.voice.whisper_transcription_adapter import WhisperTranscriptionAdapter
from src.domain.abstractions.voice import (
    AudioCodec,
    SpeechTimbre,
    VoiceActivityState,
    VoiceSessionConfig,
    VoiceSessionState,
    WebRtcSignalingMessage,
)
from src.domain.voice.voice_orchestrator import VoiceOrchestrator
from src.main import app


@pytest.mark.asyncio
async def test_whisper_transcription_and_vad():
    """Verify local Whisper transcription adapter and RMS VAD energy classification."""
    adapter = WhisperTranscriptionAdapter()

    # 1. Silence audio frame (all zeros)
    silence_frame = bytes(640)  # 320 16-bit samples = 20ms @ 16kHz
    vad_state = adapter.detect_voice_activity(silence_frame, sensitivity=0.65)
    assert vad_state == VoiceActivityState.SILENCE

    # 2. Synthetic speech audio frame (high energy waveform)
    import struct
    speech_samples = [int(15000 * (i % 2 * 2 - 1)) for i in range(320)]
    speech_frame = struct.pack("<320h", *speech_samples)
    vad_state_speech = adapter.detect_voice_activity(speech_frame, sensitivity=0.65)
    assert vad_state_speech == VoiceActivityState.SPEECH_DETECTED

    # 3. Audio transcription
    res = await adapter.transcribe_audio(speech_frame, sample_rate_hz=16000)
    assert res.text is not None
    assert len(res.text) > 0
    assert res.confidence > 0.9
    assert res.is_final is True


@pytest.mark.asyncio
async def test_speech_synthesis_streaming():
    """Verify streaming speech synthesis produces valid PCM16 audio chunks."""
    adapter = SpeechSynthesisAdapter(default_sample_rate_hz=16000)

    chunks = await adapter.synthesize_speech(
        text="Sovereign edge speech synthesis test with sub-250ms TTFAB.",
        voice_timbre=SpeechTimbre.NEURAL_NATURAL,
        speed=1.0,
    )

    assert len(chunks) > 0
    assert chunks[0].format == AudioCodec.PCM16
    assert chunks[0].sample_rate_hz == 16000
    assert len(chunks[0].audio_bytes) > 0
    assert chunks[-1].is_last is True


@pytest.mark.asyncio
async def test_webrtc_signaling_state_machine():
    """Verify WebRTC SDP offer/answer exchange and ICE candidate trickle."""
    adapter = WebRtcSignalingAdapter()

    config = VoiceSessionConfig(
        tenant_id="tn_voice_test",
        user_id="usr_field_ops",
    )
    session = await adapter.create_session(config)
    assert session.state == VoiceSessionState.INITIALIZING
    assert session.session_id.startswith("vcs_")

    # Send SDP offer
    offer_msg = WebRtcSignalingMessage(
        session_id=session.session_id,
        message_type="offer",
        sdp="v=0\r\no=- 12345 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n",
    )
    reply = await adapter.handle_signal(offer_msg)
    assert reply.message_type == "answer"
    assert reply.sdp is not None
    assert "opus/48000" in reply.sdp

    # Send ICE candidate
    ice_msg = WebRtcSignalingMessage(
        session_id=session.session_id,
        message_type="ice_candidate",
        candidate="candidate:1 1 UDP 2130706431 192.168.1.5 50000 typ host",
    )
    ice_reply = await adapter.handle_signal(ice_msg)
    assert ice_reply.message_type == "ice_ack"

    updated_session = await adapter.get_session(session.session_id)
    assert updated_session is not None
    assert updated_session.state == VoiceSessionState.CONNECTED


@pytest.mark.asyncio
async def test_voice_orchestrator_turn_lifecycle():
    """Verify full-duplex conversational voice turn with latency telemetry."""
    whisper = WhisperTranscriptionAdapter()
    synth = SpeechSynthesisAdapter()
    signaling = WebRtcSignalingAdapter()

    orchestrator = VoiceOrchestrator(
        transcription_adapter=whisper,
        synthesis_adapter=synth,
        signaling_adapter=signaling,
    )

    config = VoiceSessionConfig(tenant_id="tn_voice_turn_test")
    session = await orchestrator.initiate_session(config)

    dummy_audio = bytes(1600)  # 50ms audio

    turn, chunks = await orchestrator.process_voice_turn(
        session_id=session.session_id,
        audio_bytes=dummy_audio,
        response_generator="Local knowledge retrieved successfully in 0.4ms.",
        voice_timbre=SpeechTimbre.WARM_CONVERSATIONAL,
    )

    assert turn.session_id == session.session_id
    assert turn.agent_response_text == "Local knowledge retrieved successfully in 0.4ms."
    assert turn.time_to_transcribe_ms >= 0.0
    assert turn.time_to_first_audio_byte_ms >= 0.0
    assert turn.total_turn_duration_ms >= 0.0
    assert len(chunks) > 0

    # Verify session turns history
    turns = orchestrator.get_session_turns(session.session_id)
    assert len(turns) == 1

    # Verify telemetry
    telemetry = await orchestrator.get_telemetry("tn_voice_turn_test")
    assert telemetry.active_sessions_count >= 1
    assert telemetry.average_turn_latency_ms > 0.0


@pytest.mark.asyncio
async def test_voice_rest_endpoints():
    """Verify FastAPI REST endpoints for voice session, signaling, and synthesis."""
    from src.config import settings

    transport = ASGITransport(app=app)
    admin_headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create session
        res = await client.post(
            "/v1/tenants/tn_rest_voice/voice/session",
            headers=admin_headers,
            json={
                "user_id": "usr_test",
                "sample_rate_hz": 16000,
                "vad_sensitivity": 0.7,
                "selected_voice": "neural_natural",
                "audio_codec": "pcm16",
            },
        )
        assert res.status_code == 200
        session_data = res.json()
        session_id = session_data["session_id"]
        assert session_id.startswith("vcs_")

        # 2. WebRTC signal
        signal_res = await client.post(
            "/v1/tenants/tn_rest_voice/voice/signal",
            headers=admin_headers,
            json={
                "session_id": session_id,
                "message_type": "offer",
                "sdp": "v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n",
            },
        )
        assert signal_res.status_code == 200
        assert signal_res.json()["message_type"] == "answer"

        # 3. Transcribe audio
        audio_b64 = base64.b64encode(bytes(640)).decode("ascii")
        trans_res = await client.post(
            "/v1/tenants/tn_rest_voice/voice/transcribe",
            headers=admin_headers,
            json={
                "audio_base64": audio_b64,
                "sample_rate_hz": 16000,
            },
        )
        assert trans_res.status_code == 200
        assert "text" in trans_res.json()

        # 4. Synthesize speech
        synth_res = await client.post(
            "/v1/tenants/tn_rest_voice/voice/synthesize",
            headers=admin_headers,
            json={
                "text": "Streaming voice synthesis test.",
                "selected_voice": "neural_natural",
                "speed": 1.0,
            },
        )
        assert synth_res.status_code == 200
        synth_data = synth_res.json()
        assert synth_data["chunks_count"] > 0
        assert len(synth_data["audio_base64"]) > 0

        # 5. Full Turn
        turn_res = await client.post(
            "/v1/tenants/tn_rest_voice/voice/turn",
            headers=admin_headers,
            json={
                "session_id": session_id,
                "audio_base64": audio_b64,
                "selected_voice": "neural_natural",
            },
        )
        assert turn_res.status_code == 200
        turn_data = turn_res.json()
        assert "turn" in turn_data
        assert turn_data["turn"]["session_id"] == session_id

        # 6. Get session turns
        session_status_res = await client.get(
            f"/v1/tenants/tn_rest_voice/voice/session/{session_id}",
            headers=admin_headers,
        )
        assert session_status_res.status_code == 200
        assert len(session_status_res.json()["turns"]) >= 1

        # 7. Admin telemetry
        telemetry_res = await client.get(
            "/v1/admin/voice/telemetry",
            headers=admin_headers,
        )
        assert telemetry_res.status_code == 200
        assert "whisper_engine" in telemetry_res.json()
