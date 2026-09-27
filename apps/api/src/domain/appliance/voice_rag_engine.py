"""Domain Service for Sovereign Offline Full-Duplex Voice RAG Engine (M127).

Orchestrates an end-to-end voice-activated retrieval and answer generation pipeline:
  [Raw Audio In] ──► Local Whisper ASR (VAD Endpointing)
                 ──► Sovereign Hybrid Retrieval (Vector + FTS5)
                 ──► Local SLM Grounded Synthesis
                 ──► Piper Neural TTS (Streaming Audio Out)
Pure domain layer with zero infrastructure or framework imports.
"""

import base64
import logging
import time
import uuid
from collections.abc import Callable

from src.domain.abstractions.appliance import (
    VoiceRAGQueryRequest,
    VoiceRAGQueryResponse,
)
from src.domain.abstractions.voice import (
    SpeechSynthesisProtocol,
    SpeechTimbre,
    VoiceTranscriptionProtocol,
)

logger = logging.getLogger(__name__)


class SovereignVoiceRAGEngine:
    """Production-grade offline voice RAG engine for air-gapped sovereign appliances."""

    def __init__(
        self,
        transcription_service: VoiceTranscriptionProtocol,
        synthesis_service: SpeechSynthesisProtocol,
        hybrid_search_fn: Callable[..., any] | None = None,
        synthesis_fn: Callable[[str, list[dict]], str] | None = None,
    ) -> None:
        self.transcription = transcription_service
        self.synthesis = synthesis_service
        self.search_fn = hybrid_search_fn
        self.synthesis_fn = synthesis_fn or self._default_grounded_synthesis

    def _default_grounded_synthesis(
        self, query: str, context_chunks: list[dict]
    ) -> str:
        """Deterministic, grounded tactical domain synthesis when SLM is offline."""
        if not context_chunks:
            return f"Regarding your inquiry on '{query}', no matching sovereign records were found in the local index."

        top_chunk = context_chunks[0]
        snippet = top_chunk.get("content", "").strip()
        if len(snippet) > 280:
            snippet = snippet[:280] + "..."
        doc_id = top_chunk.get("document_id", "local_corpus")
        return f"Based on verified sovereign document '{doc_id}': {snippet}"

    async def execute_voice_rag(
        self, request: VoiceRAGQueryRequest
    ) -> VoiceRAGQueryResponse:
        """Executes full-duplex voice RAG: Audio -> ASR -> Retrieval -> LLM -> TTS -> Audio."""
        t_start = time.perf_counter()
        session_id = f"vrag_{uuid.uuid4().hex[:12]}"

        # 1. Decode raw audio bytes
        try:
            audio_bytes = base64.b64decode(request.audio_bytes_base64)
        except Exception as exc:
            raise ValueError(
                f"Invalid base64 audio payload in voice RAG request: {exc}"
            ) from exc

        # 2. Whisper ASR Transcription
        t_asr_start = time.perf_counter()
        asr_result = await self.transcription.transcribe_audio(
            audio_bytes,
            sample_rate_hz=request.sample_rate_hz,
        )
        t_asr_end = time.perf_counter()
        asr_latency_ms = (t_asr_end - t_asr_start) * 1000.0

        query_text = asr_result.text.strip()
        if not query_text:
            query_text = "Status check on sovereign system"

        # 3. Sovereign Hybrid Retrieval
        t_ret_start = time.perf_counter()
        citations: list[dict] = []
        if self.search_fn:
            try:
                retrieval_res = await self.search_fn(
                    tenant_id=request.tenant_id,
                    query=query_text,
                    top_k=request.top_k,
                )
                # Handle either EdgeSearchResponse or dict/list
                if hasattr(retrieval_res, "results"):
                    for item in retrieval_res.results[: request.top_k]:
                        citations.append(
                            {
                                "chunk_id": getattr(item, "chunk_id", ""),
                                "document_id": getattr(item, "document_id", ""),
                                "content": getattr(item, "content", ""),
                                "score": getattr(item, "score", 0.0),
                            }
                        )
                elif isinstance(retrieval_res, list):
                    citations.extend(retrieval_res[: request.top_k])
            except Exception as exc:
                logger.warning(f"Sovereign search non-fatal fallback: {exc}")
        t_ret_end = time.perf_counter()
        retrieval_latency_ms = (t_ret_end - t_ret_start) * 1000.0

        # 4. Local Grounded Generation
        t_syn_start = time.perf_counter()
        try:
            answer_text = self.synthesis_fn(query_text, citations)
        except Exception as exc:
            logger.warning(f"Synthesis fallback: {exc}")
            answer_text = self._default_grounded_synthesis(query_text, citations)
        t_syn_end = time.perf_counter()
        synthesis_latency_ms = (t_syn_end - t_syn_start) * 1000.0

        # 5. Piper Neural Speech Synthesis
        t_tts_start = time.perf_counter()
        timbre_val = SpeechTimbre.NEURAL_NATURAL
        try:
            timbre_val = SpeechTimbre(request.timbre)
        except Exception:
            pass

        audio_chunks = await self.synthesis.synthesize_speech(
            text=answer_text,
            voice_timbre=timbre_val,
            speed=1.0,
        )
        t_tts_end = time.perf_counter()
        tts_latency_ms = (t_tts_end - t_tts_start) * 1000.0

        # Assemble synthesized audio
        combined_audio = b"".join(c.audio_bytes for c in audio_chunks)
        encoded_audio = base64.b64encode(combined_audio).decode("ascii")
        total_audio_duration_ms = sum(c.duration_ms for c in audio_chunks)

        t_total_end = time.perf_counter()
        total_latency_ms = (t_total_end - t_start) * 1000.0

        return VoiceRAGQueryResponse(
            session_id=session_id,
            tenant_id=request.tenant_id,
            transcribed_text=query_text,
            answer_text=answer_text,
            citations=citations,
            audio_bytes_base64=encoded_audio,
            audio_format="pcm16",
            audio_duration_ms=total_audio_duration_ms,
            asr_latency_ms=asr_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            synthesis_latency_ms=synthesis_latency_ms,
            tts_latency_ms=tts_latency_ms,
            total_latency_ms=total_latency_ms,
        )
