"""FastAPI Routers for Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis (M100).

Exposes administrative telemetry and tenant-scoped WebRTC voice endpoints for:
- Full-duplex WebRTC session creation and SDP/ICE signaling
- In-process Whisper speech recognition and VAD endpointing
- Low-latency streaming speech synthesis with neural vocal timbres
- Turn-taking latency telemetry (TTT, TTFAB, total turn roundtrip)

Hexagonal Boundary: Only imports domain abstractions and resolves adapters via container.
"""

import asyncio
import base64
import json
import logging
import secrets
import time
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from pydantic import BaseModel, Field

from src.adapters.api.security import (
    identity_provider,
    verify_admin_key,
    verify_tenant_or_admin,
)
from src.config import settings
from src.container import container
from src.domain.abstractions.voice import (
    AudioCodec,
    SpeechTimbre,
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionTelemetry,
    VoiceStreamControlMessage,
    VoiceStreamEventType,
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

stream_router = APIRouter(
    prefix="/v1/tenants/{tenantId}/voice",
    tags=["voice", "streaming"],
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


# ── Real-Time Audio Streaming WebSocket Endpoints ────────────────────────────


async def authenticate_websocket(
    websocket: WebSocket,
    tenantId: str,
) -> bool:
    """Authenticates a WebSocket connection using token/admin_key in query params or headers."""
    admin_key = (
        websocket.headers.get("x-admin-master-key")
        or websocket.query_params.get("admin_key")
    )
    if admin_key and secrets.compare_digest(admin_key, settings.ADMIN_MASTER_KEY):
        return True

    token = websocket.headers.get("authorization") or websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication credentials")
        return False

    clean_token = token[7:] if token.lower().startswith("bearer ") else token

    if secrets.compare_digest(clean_token, settings.ADMIN_MASTER_KEY):
        return True

    try:
        user_ctx = await identity_provider.validate_token(clean_token)
        if "admin" not in user_ctx.roles and user_ctx.tenant_id != tenantId:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Tenancy boundary violation")
            return False
        return True
    except Exception as exc:
        logger.warning("WebSocket auth failed for tenant %s: %s", tenantId, exc)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return False


@stream_router.websocket("/stream/{sessionId}")
@stream_router.websocket("/ws/{sessionId}")
async def voice_stream_websocket(
    websocket: WebSocket,
    tenantId: str,
    sessionId: str,
) -> None:
    """Full-duplex real-time audio streaming WebSocket with sub-300ms TTFAB, VAD endpointing, and barge-in."""
    authenticated = await authenticate_websocket(websocket, tenantId)
    if not authenticated:
        return

    await websocket.accept()

    # Parse session configuration from query parameters
    query_params = websocket.query_params
    sensitivity = float(query_params.get("sensitivity", 0.65))
    silence_threshold_ms = int(query_params.get("silence_threshold_ms", 400))
    speed = float(query_params.get("speed", 1.0))
    voice_str = query_params.get("voice", SpeechTimbre.NEURAL_NATURAL.value)
    try:
        selected_voice = SpeechTimbre(voice_str)
    except ValueError:
        selected_voice = SpeechTimbre.NEURAL_NATURAL

    await container.voice_stream_service.register_stream(
        session_id=sessionId,
        sensitivity=sensitivity,
        silence_threshold_ms=silence_threshold_ms,
        selected_voice=selected_voice,
        speed=speed,
    )

    # Initial session ready handshake
    session_ready_msg = VoiceStreamControlMessage(
        event_type=VoiceStreamEventType.SESSION_READY,
        session_id=sessionId,
        payload={
            "status": "ready",
            "codec": AudioCodec.PCM16.value,
            "sample_rate_hz": 16000,
            "channels": 1,
            "frame_size_bytes": 640,
            "selected_voice": selected_voice.value,
        },
    )
    await websocket.send_json(session_ready_msg.model_dump(mode="json"))

    active_agent_task: asyncio.Task | None = None

    async def rag_copilot_response(user_query: str) -> str:
        from src.domain.abstractions.search import SearchQuery

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
            logger.warning("Streaming voice search failed for tenant %s: %s", tenantId, exc)

        return f"Voice query received: '{user_query}'. No grounded knowledge matches found for tenant {tenantId}."

    async def run_agent_turn(audio_bytes: bytes) -> None:
        try:
            async for chunk_or_msg in container.voice_stream_service.process_utterance(
                session_id=sessionId,
                audio_bytes=audio_bytes,
                response_generator=rag_copilot_response,
                sample_rate_hz=16000,
            ):
                if isinstance(chunk_or_msg, VoiceStreamControlMessage):
                    await websocket.send_json(chunk_or_msg.model_dump(mode="json"))
                elif hasattr(chunk_or_msg, "audio_bytes"):
                    await websocket.send_bytes(chunk_or_msg.audio_bytes)
        except asyncio.CancelledError:
            logger.info("Agent turn processing cancelled (barge-in) for session %s", sessionId)
            raise
        except Exception as err:
            logger.error("Error running streaming agent turn for session %s: %s", sessionId, err)
            await websocket.send_json({
                "event_type": VoiceStreamEventType.ERROR.value,
                "session_id": sessionId,
                "payload": {"error": str(err)},
            })

    try:
        while True:
            message = await websocket.receive()
            msg_type = message.get("type")

            if msg_type == "websocket.disconnect":
                break

            # Handle raw PCM16 audio frames
            if message.get("bytes"):
                raw_bytes = message["bytes"]
                messages, completed_audio = await container.voice_stream_service.ingest_audio_frame(
                    session_id=sessionId,
                    frame_bytes=raw_bytes,
                )
                for msg in messages:
                    await websocket.send_json(msg.model_dump(mode="json"))

                if completed_audio:
                    if active_agent_task and not active_agent_task.done():
                        active_agent_task.cancel()
                    active_agent_task = asyncio.create_task(run_agent_turn(completed_audio))
                    stream_state = container.voice_stream_service.get_stream_state(sessionId)
                    if stream_state:
                        stream_state.active_agent_task = active_agent_task

            # Handle JSON control messages
            elif message.get("text"):
                raw_text = message["text"]
                try:
                    control_data = json.loads(raw_text)
                    event_type = control_data.get("event_type")

                    if event_type == "ping":
                        await websocket.send_json({
                            "event_type": VoiceStreamEventType.PONG.value,
                            "session_id": sessionId,
                            "payload": {"timestamp": time.time()},
                        })
                    elif event_type == "interrupt":
                        interruption = await container.voice_stream_service.interrupt(
                            session_id=sessionId,
                            reason=control_data.get("reason", "client_interrupt"),
                        )
                        if active_agent_task and not active_agent_task.done():
                            active_agent_task.cancel()
                            active_agent_task = None
                        await websocket.send_json({
                            "event_type": VoiceStreamEventType.INTERRUPTED.value,
                            "session_id": sessionId,
                            "payload": interruption.model_dump(mode="json"),
                        })
                    elif event_type == "text_input":
                        user_text = control_data.get("text", "")
                        if active_agent_task and not active_agent_task.done():
                            active_agent_task.cancel()

                        async def run_text_turn(t_input: str) -> None:
                            try:
                                yield_trans = VoiceStreamControlMessage(
                                    event_type=VoiceStreamEventType.TRANSCRIPT_FINAL,
                                    session_id=sessionId,
                                    payload={"turn_id": f"vct_txt_{time.time_ns():x}", "text": t_input, "confidence": 1.0},
                                )
                                await websocket.send_json(yield_trans.model_dump(mode="json"))

                                agent_resp = await rag_copilot_response(t_input)
                                yield_resp = VoiceStreamControlMessage(
                                    event_type=VoiceStreamEventType.AGENT_TEXT_DELTA,
                                    session_id=sessionId,
                                    payload={"delta": agent_resp},
                                )
                                await websocket.send_json(yield_resp.model_dump(mode="json"))

                                state = container.voice_stream_service.get_stream_state(sessionId)
                                voice = state.selected_voice if state else SpeechTimbre.NEURAL_NATURAL
                                speed_val = state.speed if state else 1.0

                                async for chunk in container.voice_orchestrator._synthesis.stream_speech(
                                    text=agent_resp,
                                    voice_timbre=voice,
                                    speed=speed_val,
                                ):
                                    await websocket.send_bytes(chunk.audio_bytes)

                                await websocket.send_json({
                                    "event_type": VoiceStreamEventType.TURN_COMPLETE.value,
                                    "session_id": sessionId,
                                    "payload": {"turn_id": f"vct_txt_{time.time_ns():x}", "status": "completed"},
                                })
                            except asyncio.CancelledError:
                                logger.info("Text turn cancelled for session %s", sessionId)
                            except Exception as e:
                                logger.error("Text turn error: %s", e)

                        active_agent_task = asyncio.create_task(run_text_turn(user_text))
                        stream_state = container.voice_stream_service.get_stream_state(sessionId)
                        if stream_state:
                            stream_state.active_agent_task = active_agent_task

                except json.JSONDecodeError:
                    await websocket.send_json({
                        "event_type": VoiceStreamEventType.ERROR.value,
                        "session_id": sessionId,
                        "payload": {"error": "Invalid JSON format"},
                    })

    except WebSocketDisconnect:
        logger.info("Voice stream WebSocket disconnected for session %s", sessionId)
    except Exception as exc:
        logger.warning("Voice stream WebSocket error for session %s: %s", sessionId, exc)
    finally:
        if active_agent_task and not active_agent_task.done():
            active_agent_task.cancel()
        await container.voice_stream_service.unregister_stream(sessionId)

