"""Voice Stream Domain Service for Low-Latency Full-Duplex Real-Time Audio (M114).

Orchestrates live bi-directional audio streaming over WebSocket:
- Frame-level Voice Activity Detection (VAD) on 20ms PCM16 frames
- Automatic speech endpointing without manual click-to-stop
- Instant conversational barge-in / interruption (cancels active synthesis on user speech)
- Sub-300ms Time-to-First-Audio-Byte streaming speech synthesis
- Zero-cloud audio egress guarantees and Hexagonal domain isolation

Strictly Hexagonal: Zero database, ORM, or web framework imports.
"""

import asyncio
import logging
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.domain.abstractions.voice import (
    SpeechSynthesisProtocol,
    SpeechTimbre,
    SynthesizedAudioChunk,
    TranscriptionResult,
    VoiceActivityState,
    VoiceInterruptionEvent,
    VoiceStreamControlMessage,
    VoiceStreamEventType,
    VoiceStreamServiceProtocol,
    VoiceTranscriptionProtocol,
    VoiceTurn,
    WebRtcSignalingProtocol,
)

logger = logging.getLogger(__name__)


@dataclass
class StreamSessionState:
    """Internal lifecycle and audio buffer state for an active voice stream."""

    session_id: str
    audio_buffer: bytearray = field(default_factory=bytearray)
    speech_frames_count: int = 0
    silence_frames_count: int = 0
    is_user_speaking: bool = False
    active_agent_task: asyncio.Task | None = None
    active_turn_id: str | None = None
    sensitivity: float = 0.65
    silence_threshold_frames: int = 20  # 20 * 20ms = 400ms silence endpoint
    consecutive_speech_for_barge_in: int = 3  # 3 * 20ms = 60ms speech triggers interruption
    selected_voice: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL
    speed: float = 1.0
    last_frame_at: float = field(default_factory=time.time)


class VoiceStreamService(VoiceStreamServiceProtocol):
    """Core domain service orchestrating live full-duplex voice streams & barge-in."""

    def __init__(
        self,
        transcription_adapter: VoiceTranscriptionProtocol,
        synthesis_adapter: SpeechSynthesisProtocol,
        signaling_adapter: WebRtcSignalingProtocol,
    ) -> None:
        self._transcription = transcription_adapter
        self._synthesis = synthesis_adapter
        self._signaling = signaling_adapter
        self._streams: dict[str, StreamSessionState] = {}
        self._turns_history: dict[str, list[VoiceTurn]] = {}

    async def register_stream(
        self,
        session_id: str,
        sensitivity: float = 0.65,
        silence_threshold_ms: int = 400,
        selected_voice: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> None:
        """Registers and initializes state for a live audio stream."""
        silence_frames = max(5, silence_threshold_ms // 20)
        self._streams[session_id] = StreamSessionState(
            session_id=session_id,
            sensitivity=sensitivity,
            silence_threshold_frames=silence_frames,
            selected_voice=selected_voice,
            speed=speed,
        )
        self._turns_history.setdefault(session_id, [])

    async def unregister_stream(self, session_id: str) -> None:
        """Cleans up resources and cancels running tasks for a disconnected stream."""
        state = self._streams.pop(session_id, None)
        if state and state.active_agent_task and not state.active_agent_task.done():
            state.active_agent_task.cancel()

    def get_stream_state(self, session_id: str) -> StreamSessionState | None:
        """Returns the active stream state for a session."""
        return self._streams.get(session_id)

    async def ingest_audio_frame(
        self,
        session_id: str,
        frame_bytes: bytes,
    ) -> tuple[list[VoiceStreamControlMessage], bytes | None]:
        """Ingests a 20ms audio frame, evaluates VAD, and handles endpointing / barge-in.

        Returns:
            tuple of (emitted control messages, completed speech audio bytes if endpoint detected else None)
        """
        state = self._streams.get(session_id)
        if not state:
            await self.register_stream(session_id)
            state = self._streams[session_id]

        state.last_frame_at = time.time()
        messages: list[VoiceStreamControlMessage] = []
        completed_utterance_audio: bytes | None = None

        vad_state = self._transcription.detect_voice_activity(frame_bytes, state.sensitivity)

        if vad_state == VoiceActivityState.SPEECH_DETECTED:
            if not state.is_user_speaking:
                state.is_user_speaking = True
                messages.append(
                    VoiceStreamControlMessage(
                        event_type=VoiceStreamEventType.VAD_STATE,
                        session_id=session_id,
                        payload={"state": "speech_detected", "timestamp": time.time()},
                    )
                )

            state.speech_frames_count += 1
            state.silence_frames_count = 0
            state.audio_buffer.extend(frame_bytes)

            # Conversational Barge-In: If agent is currently speaking, user speech cancels agent output
            if state.active_agent_task and not state.active_agent_task.done():
                if state.speech_frames_count >= state.consecutive_speech_for_barge_in:
                    cancelled_task = state.active_agent_task
                    state.active_agent_task = None
                    cancelled_turn = state.active_turn_id
                    state.active_turn_id = None
                    cancelled_task.cancel()

                    messages.append(
                        VoiceStreamControlMessage(
                            event_type=VoiceStreamEventType.INTERRUPTED,
                            session_id=session_id,
                            payload={
                                "reason": "user_barge_in",
                                "cancelled_turn_id": cancelled_turn,
                                "speech_frames": state.speech_frames_count,
                                "message": "Agent response cancelled due to user barge-in.",
                            },
                        )
                    )

        elif vad_state == VoiceActivityState.SILENCE:
            if state.is_user_speaking:
                state.silence_frames_count += 1
                state.audio_buffer.extend(frame_bytes)

                if state.silence_frames_count >= state.silence_threshold_frames:
                    # Speech turn endpoint reached
                    state.is_user_speaking = False
                    completed_utterance_audio = bytes(state.audio_buffer)
                    state.audio_buffer.clear()
                    state.speech_frames_count = 0
                    state.silence_frames_count = 0

                    messages.append(
                        VoiceStreamControlMessage(
                            event_type=VoiceStreamEventType.VAD_STATE,
                            session_id=session_id,
                            payload={
                                "state": "endpoint_detected",
                                "total_bytes": len(completed_utterance_audio),
                                "timestamp": time.time(),
                            },
                        )
                    )

        return messages, completed_utterance_audio

    async def interrupt(
        self,
        session_id: str,
        reason: str = "user_barge_in",
    ) -> VoiceInterruptionEvent:
        """Cancels active speech generation or synthesis task immediately."""
        state = self._streams.get(session_id)
        cancelled_turn_id = None
        frames_count = 0

        if state:
            frames_count = state.speech_frames_count
            state.is_user_speaking = False
            state.speech_frames_count = 0
            state.silence_frames_count = 0
            state.audio_buffer.clear()

            if state.active_agent_task and not state.active_agent_task.done():
                cancelled_turn_id = state.active_turn_id
                state.active_agent_task.cancel()
                state.active_agent_task = None
                state.active_turn_id = None

        return VoiceInterruptionEvent(
            session_id=session_id,
            interrupted_at=datetime.now(UTC),
            reason=reason,
            cancelled_turn_id=cancelled_turn_id,
            frames_buffered_count=frames_count,
        )

    async def process_utterance(
        self,
        session_id: str,
        audio_bytes: bytes,
        response_generator: Callable[[str], Any] | str,
        sample_rate_hz: int = 16000,
    ) -> AsyncIterator[VoiceStreamControlMessage | SynthesizedAudioChunk]:
        """Executes full STT -> Cognition -> Streaming TTS pipeline emitting real-time chunks."""
        state = self._streams.get(session_id)
        if not state:
            await self.register_stream(session_id)
            state = self._streams[session_id]

        turn_start = time.perf_counter()
        turn_id = f"vct_{time.time_ns():x}"
        state.active_turn_id = turn_id

        # 1. Transcribe audio via Whisper
        transcribe_start = time.perf_counter()
        transcription: TranscriptionResult = await self._transcription.transcribe_audio(
            audio_bytes,
            sample_rate_hz=sample_rate_hz,
        )
        time_to_transcribe_ms = (time.perf_counter() - transcribe_start) * 1000.0

        yield VoiceStreamControlMessage(
            event_type=VoiceStreamEventType.TRANSCRIPT_FINAL,
            session_id=session_id,
            payload={
                "turn_id": turn_id,
                "text": transcription.text,
                "confidence": transcription.confidence,
                "duration_ms": transcription.duration_ms,
                "latency_ms": round(time_to_transcribe_ms, 2),
            },
        )

        yield VoiceStreamControlMessage(
            event_type=VoiceStreamEventType.AGENT_THINKING,
            session_id=session_id,
            payload={"turn_id": turn_id},
        )

        # 2. Cognition Response Generator
        if callable(response_generator):
            agent_text = await response_generator(transcription.text)
        elif isinstance(response_generator, str):
            agent_text = response_generator
        else:
            agent_text = f"Acknowledged: {transcription.text}"

        yield VoiceStreamControlMessage(
            event_type=VoiceStreamEventType.AGENT_TEXT_DELTA,
            session_id=session_id,
            payload={"turn_id": turn_id, "delta": agent_text},
        )

        # 3. Streaming Neural Speech Synthesis
        synthesis_start = time.perf_counter()
        first_chunk_emitted = False
        chunks_count = 0
        time_to_first_audio_byte_ms = 0.0

        try:
            async for chunk in self._synthesis.stream_speech(
                text=agent_text,
                voice_timbre=state.selected_voice,
                speed=state.speed,
            ):
                if not first_chunk_emitted:
                    time_to_first_audio_byte_ms = (time.perf_counter() - synthesis_start) * 1000.0
                    first_chunk_emitted = True

                chunks_count += 1
                yield chunk
        except asyncio.CancelledError:
            logger.info("Voice synthesis cancelled for session %s (turn %s)", session_id, turn_id)
            raise

        total_turn_duration_ms = (time.perf_counter() - turn_start) * 1000.0

        # 4. Turn Complete Message
        voice_turn = VoiceTurn(
            turn_id=turn_id,
            session_id=session_id,
            tenant_id=session_id.split("_")[1] if "_" in session_id else "tn_voice",
            user_transcript=transcription.text,
            agent_response_text=agent_text,
            time_to_transcribe_ms=round(time_to_transcribe_ms, 2),
            time_to_first_audio_byte_ms=round(time_to_first_audio_byte_ms, 2),
            total_turn_duration_ms=round(total_turn_duration_ms, 2),
            created_at=datetime.now(UTC),
        )

        self._turns_history.setdefault(session_id, []).append(voice_turn)
        state.active_turn_id = None

        yield VoiceStreamControlMessage(
            event_type=VoiceStreamEventType.TURN_COMPLETE,
            session_id=session_id,
            payload={
                "turn": voice_turn.model_dump(mode="json"),
                "chunks_count": chunks_count,
            },
        )
