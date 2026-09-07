"""FastAPI Routers for Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis (M100).

Exposes administrative telemetry and tenant-scoped WebRTC voice endpoints for:
- Full-duplex WebRTC session creation and SDP/ICE signaling
- In-process Whisper speech recognition and VAD endpointing
- Low-latency streaming speech synthesis with neural vocal timbres
- Turn-taking latency telemetry (TTT, TTFAB, total turn roundtrip)

Hexagonal Boundary: Only imports domain abstractions and resolves adapters via container.
"""

import base64
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.adapters.api.security import verify_admin_key, verify_tenant_or_admin
from src.container import container
from src.domain.abstractions.voice import (
    AudioCodec,
    SpeechTimbre,
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionTelemetry,
    VoiceTurn,
    WebRtcSignalingMessage,
)

logger = logging.getLogger(__name__)

admin_router = APIRouter(
    prefix="/v1/admin/voice",
    tags=["voice", "admin"],
    dependencies=[Depends(verify_admin_key)],
)

tenant_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/voice",
    tags=["voice", "tenant"],
    dependencies=[Depends(verify_tenant_or_admin)],
)


# ── Request / Response DTOs ───────────────────────────────────────────────────


class CreateVoiceSessionRequest(BaseModel):
    """Parameters to initialize a new edge voice session."""

    user_id: str = Field(default="usr_anonymous")
    sample_rate_hz: int = Field(default=16000, ge=8000, le=48000)
    channels: int = Field(default=1, ge=1, le=2)
    vad_sensitivity: float = Field(default=0.65, ge=0.0, le=1.0)
    selected_voice: SpeechTimbre = Field(default=SpeechTimbre.NEURAL_NATURAL)
    audio_codec: AudioCodec = Field(default=AudioCodec.PCM16)


class TranscribeAudioRequest(BaseModel):
    """Payload containing raw or base64-encoded audio bytes for Whisper recognition."""

    audio_base64: str = Field(..., description="Base64-encoded PCM16 or WAV audio bytes")
    sample_rate_hz: int = Field(default=16000)


class SynthesizeSpeechRequest(BaseModel):
    """Text-to-speech synthesis parameters."""

    text: str = Field(..., description="Textual utterance to synthesize")
    selected_voice: SpeechTimbre = Field(default=SpeechTimbre.NEURAL_NATURAL)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class VoiceTurnRequest(BaseModel):
    """Conversational turn request submitting audio or transcript."""

    session_id: str = Field(...)
    audio_base64: str | None = Field(default=None)
    text_override: str | None = Field(default=None)
    selected_voice: SpeechTimbre = Field(default=SpeechTimbre.NEURAL_NATURAL)
    speed: float = Field(default=1.0)


class VoiceTurnResponse(BaseModel):
    """Turn execution result with latency breakdown and synthesized audio."""

    turn: VoiceTurn
    audio_base64: str
    chunks_count: int


# ── Tenant Endpoints ──────────────────────────────────────────────────────────


@tenant_router.post("/session", response_model=VoiceSession)
async def create_voice_session(
    tenantId: str,
    request: CreateVoiceSessionRequest,
) -> VoiceSession:
    """Initializes a new sovereign edge WebRTC voice session."""
    config = VoiceSessionConfig(
        tenant_id=tenantId,
        user_id=request.user_id,
        sample_rate_hz=request.sample_rate_hz,
        channels=request.channels,
        vad_sensitivity=request.vad_sensitivity,
        selected_voice=request.selected_voice,
        audio_codec=request.audio_codec,
    )
    return await container.voice_orchestrator.initiate_session(config)


@tenant_router.post("/signal", response_model=WebRtcSignalingMessage)
async def handle_webrtc_signal(
    tenantId: str,
    payload: WebRtcSignalingMessage,
) -> WebRtcSignalingMessage:
    """Exchanges WebRTC signaling payloads (SDP offers, answers, trickle ICE candidates)."""
    try:
        return await container.voice_orchestrator.process_signal(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@tenant_router.post("/transcribe")
async def transcribe_audio_stream(
    tenantId: str,
    request: TranscribeAudioRequest,
) -> dict[str, Any]:
    """Transcribes audio payload via local Whisper engine."""
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid base64 audio payload",
        ) from e

    result = await container.whisper_transcription_adapter.transcribe_audio(
        audio_bytes=audio_bytes,
        sample_rate_hz=request.sample_rate_hz,
    )
    return result.model_dump()


@tenant_router.post("/synthesize")
async def synthesize_speech_stream(
    tenantId: str,
    request: SynthesizeSpeechRequest,
) -> dict[str, Any]:
    """Synthesizes text into streaming audio chunks."""
    chunks = await container.speech_synthesis_adapter.synthesize_speech(
        text=request.text,
        voice_timbre=request.selected_voice,
        speed=request.speed,
    )
    combined_bytes = b"".join(c.audio_bytes for c in chunks)
    return {
        "text": request.text,
        "chunks_count": len(chunks),
        "total_bytes": len(combined_bytes),
        "audio_base64": base64.b64encode(combined_bytes).decode("ascii"),
        "sample_rate_hz": container.speech_synthesis_adapter.sample_rate_hz,
        "format": "pcm16",
    }


@tenant_router.post("/turn", response_model=VoiceTurnResponse)
async def process_conversational_turn(
    tenantId: str,
    request: VoiceTurnRequest,
) -> VoiceTurnResponse:
    """Processes a complete conversational turn (STT -> RAG Copilot -> Streaming TTS)."""
    audio_bytes = b""
    if request.audio_base64:
        try:
            audio_bytes = base64.b64decode(request.audio_base64)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid base64-encoded audio payload: {e}",
            ) from e

    async def rag_copilot_response(user_query: str) -> str:
        from src.domain.abstractions.retrieval import SearchQuery

        try:
            search_res = await container.search_service.search(
                SearchQuery(
                    query=user_query,
                    tenant_id=tenantId,
                    top_k=2,
                    enable_hybrid=True,
                )
            )
            if search_res and search_res.results:
                chunks_text = " ".join(c.content[:200].strip() for c in search_res.results[:2])
                return f"Grounded response for '{user_query}': {chunks_text}"
        except Exception as exc:
            logger.warning("Voice turn search failed for tenant %s: %s", tenantId, exc)

        return f"Voice query received: '{user_query}'. No grounded knowledge matches found for tenant {tenantId}."

    generator = request.text_override if request.text_override else rag_copilot_response

    try:
        turn, chunks = await container.voice_orchestrator.process_voice_turn(
            session_id=request.session_id,
            audio_bytes=audio_bytes,
            response_generator=generator,
            voice_timbre=request.selected_voice,
            speed=request.speed,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    combined_bytes = b"".join(c.audio_bytes for c in chunks)
    return VoiceTurnResponse(
        turn=turn,
        audio_base64=base64.b64encode(combined_bytes).decode("ascii"),
        chunks_count=len(chunks),
    )


@tenant_router.get("/session/{sessionId}")
async def get_voice_session(
    tenantId: str,
    sessionId: str,
) -> dict[str, Any]:
    """Retrieves session status and turn history."""
    session = await container.voice_orchestrator.get_session(sessionId)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Voice session {sessionId} not found",
        )
    turns = container.voice_orchestrator.get_session_turns(sessionId)
    return {
        "session": session.model_dump(),
        "turns": [t.model_dump() for t in turns],
    }


@tenant_router.delete("/session/{sessionId}")
async def terminate_voice_session(
    tenantId: str,
    sessionId: str,
) -> dict[str, bool]:
    """Terminates a voice session."""
    success = await container.voice_orchestrator.terminate_session(sessionId)
    return {"terminated": success}


# ── Admin Endpoints ───────────────────────────────────────────────────────────


@admin_router.get("/telemetry", response_model=VoiceSessionTelemetry)
async def get_voice_telemetry() -> VoiceSessionTelemetry:
    """Retrieves global telemetry and acoustic latency profiles across voice sessions."""
    return await container.voice_orchestrator.get_telemetry("global_admin")
