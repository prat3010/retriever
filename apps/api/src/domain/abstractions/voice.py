"""Domain Abstractions for Sovereign Edge Voice & Local Whisper / WebRTC Speech Synthesis (M100).

Defines pure domain entities, enums, data models, and abstract protocols for:
- Full-duplex WebRTC voice sessions and real-time signaling (SDP/ICE)
- On-device and edge Whisper speech-to-text transcription with VAD endpointing
- Low-latency streaming speech synthesis with neural vocal modulation
- Turn-taking latency telemetry (TTT, TTFAB, total conversational latency)
- Zero-cloud audio egress guarantees and tenant isolation

Strictly Hexagonal: Zero database, ORM, or web framework imports.
"""

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class AudioCodec(StrEnum):
    """Supported audio codecs for sovereign edge voice streaming."""

    PCM16 = "pcm16"
    OPUS = "opus"
    WAV = "wav"
    MP3 = "mp3"


class VoiceSessionState(StrEnum):
    """Lifecycle state of a real-time WebRTC voice session."""

    INITIALIZING = "initializing"
    SIGNALING = "signaling"
    CONNECTED = "connected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    THINKING = "thinking"
    SPEAKING = "speaking"
    DISCONNECTED = "disconnected"


class VoiceActivityState(StrEnum):
    """Voice Activity Detection (VAD) energy classification state."""

    SILENCE = "silence"
    SPEECH_DETECTED = "speech_detected"
    ENDPOINT_DETECTED = "endpoint_detected"


class SpeechTimbre(StrEnum):
    """Voice timbre and synthesis profile presets."""

    NEURAL_NATURAL = "neural_natural"
    NEURAL_FAST = "neural_fast"
    WARM_CONVERSATIONAL = "warm_conversational"
    CRISP_AUTHORITATIVE = "crisp_authoritative"


class VoiceSessionConfig(BaseModel):
    """Configuration parameters for a sovereign edge voice session."""

    tenant_id: str = Field(..., description="Tenant workspace identifier")
    user_id: str = Field(default="usr_anonymous", description="User identifier initiating voice stream")
    sample_rate_hz: int = Field(default=16000, ge=8000, le=48000, description="Audio sample rate in Hertz")
    channels: int = Field(default=1, ge=1, le=2, description="Channel count (1=mono, 2=stereo)")
    vad_sensitivity: float = Field(default=0.65, ge=0.0, le=1.0, description="VAD energy threshold sensitivity")
    vad_silence_duration_ms: int = Field(default=400, ge=100, le=2000, description="Silence duration for turn endpoint")
    selected_voice: SpeechTimbre = Field(default=SpeechTimbre.NEURAL_NATURAL, description="Synthesis timbre preset")
    audio_codec: AudioCodec = Field(default=AudioCodec.PCM16, description="Preferred audio codec")


class VoiceSession(BaseModel):
    """Active WebRTC voice session entity."""

    session_id: str = Field(default_factory=lambda: f"vcs_{uuid.uuid4().hex[:12]}")
    tenant_id: str
    user_id: str
    state: VoiceSessionState = VoiceSessionState.INITIALIZING
    config: VoiceSessionConfig
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    connected_at: datetime | None = None
    total_turns: int = Field(default=0)
    last_ping_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    meta_data: dict[str, Any] = Field(default_factory=dict)


class WebRtcSignalingMessage(BaseModel):
    """Signaling payload exchanged during WebRTC session establishment."""

    session_id: str = Field(..., description="Target voice session identifier")
    message_type: str = Field(..., description="Signal type: offer, answer, ice_candidate, hangup")
    sdp: str | None = Field(default=None, description="SDP session description string")
    candidate: str | None = Field(default=None, description="ICE candidate descriptor string")
    sdp_mid: str | None = Field(default=None, description="SDP media stream identifier")
    sdp_mline_index: int | None = Field(default=None, description="SDP media line index")


class TranscriptionResult(BaseModel):
    """Speech-to-text recognition output produced by local Whisper engine."""

    text: str = Field(..., description="Transcribed textual string")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Acoustic model confidence score")
    language: str = Field(default="en", description="Detected or configured spoken language")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Audio segment duration in milliseconds")
    is_final: bool = Field(default=True, description="True if segment is definitive, False if partial preview")
    words_count: int = Field(default=0, ge=0, description="Total recognized words")


class SynthesizedAudioChunk(BaseModel):
    """Streaming binary audio packet emitted by speech synthesis adapter."""

    audio_bytes: bytes = Field(..., description="Raw binary audio payload")
    sample_rate_hz: int = Field(default=16000, description="Playback sample rate in Hertz")
    chunk_index: int = Field(default=0, ge=0, description="Monotonic sequence number of audio chunk")
    duration_ms: float = Field(default=0.0, ge=0.0, description="Duration represented by this chunk in ms")
    is_last: bool = Field(default=False, description="True if this chunk terminates the synthesized utterance")
    format: AudioCodec = Field(default=AudioCodec.PCM16, description="Encoding format")


class VoiceTurn(BaseModel):
    """A completed conversational turn between user speech and agent voice."""

    turn_id: str = Field(default_factory=lambda: f"vct_{uuid.uuid4().hex[:12]}")
    session_id: str
    tenant_id: str
    user_transcript: str
    agent_response_text: str
    time_to_transcribe_ms: float = Field(default=0.0, description="Latency from turn endpoint to final transcript")
    time_to_first_audio_byte_ms: float = Field(default=0.0, description="Latency from transcript to first audio chunk")
    total_turn_duration_ms: float = Field(default=0.0, description="Total conversational round-trip latency")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VoiceSessionTelemetry(BaseModel):
    """Operational telemetry and acoustic performance indicators."""

    active_sessions_count: int = Field(default=0)
    average_turn_latency_ms: float = Field(default=0.0)
    audio_frames_processed: int = Field(default=0)
    vad_speech_events_count: int = Field(default=0)
    whisper_engine: str = Field(default="whisper_cpp_embedded")
    synthesis_engine: str = Field(default="edge_neural_tts")


# ── Domain Abstract Protocols ──────────────────────────────────────────────────


class VoiceTranscriptionProtocol(Protocol):
    """Abstract port for on-device and edge Whisper speech recognition."""

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        sample_rate_hz: int = 16000,
    ) -> TranscriptionResult:
        """Transcribes raw PCM/WAV audio bytes into text."""
        ...

    def detect_voice_activity(
        self,
        audio_frame: bytes,
        sensitivity: float = 0.65,
    ) -> VoiceActivityState:
        """Evaluates RMS energy and zero-crossing rate of a 20ms audio frame."""
        ...


class SpeechSynthesisProtocol(Protocol):
    """Abstract port for low-latency streaming speech synthesis."""

    async def synthesize_speech(
        self,
        text: str,
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> list[SynthesizedAudioChunk]:
        """Synthesizes text into a sequence of binary audio chunks."""
        ...

    def stream_speech(
        self,
        text: str,
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> AsyncIterator[SynthesizedAudioChunk]:
        """Asynchronously yields streaming audio chunks for sub-250ms TTFAB."""
        ...


class WebRtcSignalingProtocol(Protocol):
    """Abstract port for managing WebRTC SDP and ICE signaling."""

    async def create_session(self, config: VoiceSessionConfig) -> VoiceSession:
        """Initializes a new WebRTC voice session."""
        ...

    async def handle_signal(self, payload: WebRtcSignalingMessage) -> WebRtcSignalingMessage:
        """Handles incoming SDP offers/answers or ICE candidates."""
        ...

    async def close_session(self, session_id: str) -> bool:
        """Terminates an active voice session and releases media resources."""
        ...

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Retrieves session state by identifier."""
        ...

    async def list_active_sessions(self, tenant_id: str) -> list[VoiceSession]:
        """Lists active voice sessions for a tenant."""
        ...
