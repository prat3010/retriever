"""Speech Synthesis Adapter for Sovereign Edge Voice (M100).

Implements SpeechSynthesisProtocol for low-latency streaming TTS:
- Generates binary PCM16 audio frames with proper sample headers
- Simulates sub-250ms streaming chunks (Time-to-First-Audio-Byte)
- Adapts neural timbre, speaking rate, and vocal pitch
"""

import asyncio
import math
import struct
from collections.abc import AsyncIterator

from src.domain.abstractions.voice import (
    AudioCodec,
    SpeechSynthesisProtocol,
    SpeechTimbre,
    SynthesizedAudioChunk,
)


class SpeechSynthesisAdapter(SpeechSynthesisProtocol):
    """Local edge speech synthesis adapter producing streaming PCM16 audio frames."""

    def __init__(self, default_sample_rate_hz: int = 16000) -> None:
        self.sample_rate_hz = default_sample_rate_hz

    def _generate_synthetic_tone_chunk(
        self,
        duration_ms: float,
        freq_hz: float = 440.0,
        volume: float = 0.3,
    ) -> bytes:
        """Generates a small synthesized sine wave audio chunk in 16-bit signed mono PCM."""
        sample_count = int((duration_ms / 1000.0) * self.sample_rate_hz)
        samples = []
        for i in range(sample_count):
            t = float(i) / self.sample_rate_hz
            # Generate harmonic tone simulating human formant resonance
            sine_val = math.sin(2.0 * math.pi * freq_hz * t) * 0.7 + math.sin(4.0 * math.pi * freq_hz * t) * 0.3
            sample_val = int(sine_val * volume * 32767.0)
            # Clamp to 16-bit range
            sample_val = max(-32768, min(32767, sample_val))
            samples.append(sample_val)

        return struct.pack(f"<{len(samples)}h", *samples)

    async def synthesize_speech(
        self,
        text: str,
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> list[SynthesizedAudioChunk]:
        """Synthesizes text into a list of sequential binary audio chunks."""
        chunks: list[SynthesizedAudioChunk] = []
        async for chunk in self.stream_speech(text, voice_timbre, speed):
            chunks.append(chunk)
        return chunks

    async def stream_speech(
        self,
        text: str,
        voice_timbre: SpeechTimbre = SpeechTimbre.NEURAL_NATURAL,
        speed: float = 1.0,
    ) -> AsyncIterator[SynthesizedAudioChunk]:
        """Asynchronously streams audio chunks for low-latency WebRTC playback."""
        words = text.split() if text else ["Ready"]
        total_chunks = max(1, len(words) // 3)

        # Base fundamental frequency based on timbre profile
        base_freq = {
            SpeechTimbre.NEURAL_NATURAL: 220.0,
            SpeechTimbre.NEURAL_FAST: 260.0,
            SpeechTimbre.WARM_CONVERSATIONAL: 180.0,
            SpeechTimbre.CRISP_AUTHORITATIVE: 195.0,
        }.get(voice_timbre, 220.0)

        chunk_duration_ms = 120.0 / max(0.5, min(2.0, speed))

        for idx in range(total_chunks):
            is_last = idx == total_chunks - 1
            audio_bytes = self._generate_synthetic_tone_chunk(
                duration_ms=chunk_duration_ms,
                freq_hz=base_freq + (idx * 15.0),
                volume=0.25,
            )

            # Tiny async delay simulating streaming neural vocoder synthesis (~12ms per chunk)
            await asyncio.sleep(0.012)

            yield SynthesizedAudioChunk(
                audio_bytes=audio_bytes,
                sample_rate_hz=self.sample_rate_hz,
                chunk_index=idx,
                duration_ms=chunk_duration_ms,
                is_last=is_last,
                format=AudioCodec.PCM16,
            )
