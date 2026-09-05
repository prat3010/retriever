"""Voice Orchestrator Domain Service for Sovereign Edge Voice & WebRTC (M100).

Orchestrates full-duplex voice sessions:
- Coordinates WebRTC SDP signaling and ICE connectivity
- Ingests audio frames with continuous Voice Activity Detection (VAD)
- Drives Whisper speech recognition on speech endpointing
- Synthesizes conversational agent replies into streaming audio chunks
- Tracks granular turn latency metrics (TTT, TTFAB, total round-trip)

Strictly Hexagonal: Only depends on domain abstractions.
"""

import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from src.domain.abstractions.voice import (
    SpeechSynthesisProtocol,
    SpeechTimbre,
    SynthesizedAudioChunk,
    TranscriptionResult,
    VoiceActivityState,
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionState,
    VoiceSessionTelemetry,
    VoiceTranscriptionProtocol,
    VoiceTurn,
    WebRtcSignalingMessage,
    WebRtcSignalingProtocol,
)


class VoiceOrchestrator:
    """Core domain orchestrator managing full-duplex edge voice sessions."""

    def __init__(
        self,
        transcription_adapter: VoiceTranscriptionProtocol,
        synthesis_adapter: SpeechSynthesisProtocol,
        signaling_adapter: WebRtcSignalingProtocol,
    ) -> None:
        self._transcription = transcription_adapter
        self._synthesis = synthesis_adapter
        self._signaling = signaling_adapter
        self._turns_history: dict[str, list[VoiceTurn]] = {}  # session_id -> list[VoiceTurn]
        self._audio_frames_count: int = 0
        self._vad_events_count: int = 0

    async def initiate_session(self, config: VoiceSessionConfig) -> VoiceSession:
        """Initializes a new sovereign edge voice session."""
        session = await self._signaling.create_session(config)
        self._turns_history[session.session_id] = []
        return session

    async def process_signal(self, payload: WebRtcSignalingMessage) -> WebRtcSignalingMessage:
        """Processes incoming WebRTC signaling messages (offers, answers, ICE candidates)."""
        return await self._signaling.handle_signal(payload)

    async def terminate_session(self, session_id: str) -> bool:
        """Terminates an active session."""
        return await self._signaling.close_session(session_id)

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Retrieves session status."""
        return await self._signaling.get_session(session_id)

    def analyze_frame_vad(
        self,
        audio_frame: bytes,
        sensitivity: float = 0.65,
    ) -> VoiceActivityState:
        """Analyzes a 20ms audio frame for voice activity detection."""
        self._audio_frames_count += 1
        state = self._transcription.detect_voice_activity(audio_frame, sensitivity)
        if state != VoiceActivityState.SILENCE:
            self._vad_events_count += 1
        return state

    async def process_voice_turn(
        self,
        session_id: str,
        audio_bytes: bytes,
        response_generator: Any,  # Async callable or direct string generator
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> tuple[VoiceTurn, list[SynthesizedAudioChunk]]:
        """Processes a complete conversational voice turn.

        1. Transcribes audio input via Whisper.
        2. Generates conversational answer from RAG response generator.
        3. Synthesizes speech audio chunks for playback.
        4. Calculates precise latency breakdown (TTT, TTFAB, total).
        """
        session = await self._signaling.get_session(session_id)
        if not session:
            raise ValueError(f"Voice session {session_id} not found or closed")

        turn_start_time = time.perf_counter()

        # Step 1: Speech-to-Text Transcription
        session.state = VoiceSessionState.TRANSCRIBING
        transcribe_start = time.perf_counter()
        transcription: TranscriptionResult = await self._transcription.transcribe_audio(
            audio_bytes,
            sample_rate_hz=session.config.sample_rate_hz,
        )
        time_to_transcribe_ms = (time.perf_counter() - transcribe_start) * 1000.0

        # Step 2: Agent Cognition / Response Generation
        session.state = VoiceSessionState.THINKING
        if callable(response_generator):
            agent_text = await response_generator(transcription.text)
        elif isinstance(response_generator, str):
            agent_text = response_generator
        else:
            agent_text = f"Acknowledged: {transcription.text}"

        # Step 3: Text-to-Speech Synthesis
        session.state = VoiceSessionState.SPEAKING
        synthesis_start = time.perf_counter()
        audio_chunks = await self._synthesis.synthesize_speech(
            text=agent_text,
            voice_timbre=voice_timbre,
            speed=speed,
        )
        time_to_first_audio_byte_ms = (time.perf_counter() - synthesis_start) * 1000.0
        total_turn_duration_ms = (time.perf_counter() - turn_start_time) * 1000.0

        # Step 4: Record Turn
        turn = VoiceTurn(
            session_id=session_id,
            tenant_id=session.tenant_id,
            user_transcript=transcription.text,
            agent_response_text=agent_text,
            time_to_transcribe_ms=round(time_to_transcribe_ms, 2),
            time_to_first_audio_byte_ms=round(time_to_first_audio_byte_ms, 2),
            total_turn_duration_ms=round(total_turn_duration_ms, 2),
            created_at=datetime.now(UTC),
        )

        session.total_turns += 1
        session.state = VoiceSessionState.LISTENING
        session.last_ping_at = datetime.now(UTC)

        turns = self._turns_history.setdefault(session_id, [])
        turns.append(turn)

        return turn, audio_chunks

    async def stream_synthesized_turn(
        self,
        text: str,
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> AsyncIterator[SynthesizedAudioChunk]:
        """Asynchronously streams audio chunks for live WebRTC audio track injection."""
        async for chunk in self._synthesis.stream_speech(text, voice_timbre, speed):
            yield chunk

    def get_session_turns(self, session_id: str) -> list[VoiceTurn]:
        """Retrieves conversational turn history for a session."""
        return self._turns_history.get(session_id, [])

    async def get_telemetry(self, tenant_id: str) -> VoiceSessionTelemetry:
        """Aggregates active voice session telemetry."""
        active_sessions = await self._signaling.list_active_sessions(tenant_id)
        all_turns = [turn for turns in self._turns_history.values() for turn in turns]

        avg_latency = (
            sum(t.total_turn_duration_ms for t in all_turns) / len(all_turns)
            if all_turns
            else 0.0
        )

        return VoiceSessionTelemetry(
            active_sessions_count=len(active_sessions),
            average_turn_latency_ms=round(avg_latency, 2),
            audio_frames_processed=self._audio_frames_count,
            vad_speech_events_count=self._vad_events_count,
            whisper_engine="whisper_cpp_sovereign_edge",
            synthesis_engine="edge_neural_tts_streamer",
        )
