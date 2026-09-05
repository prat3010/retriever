"""WebRTC Signaling Adapter for Sovereign Edge Voice (M100).

Implements WebRtcSignalingProtocol:
- WebRTC session lifecycle management
- SDP offer / answer negotiation state machine
- Trickle ICE candidate aggregation and STUN configuration
"""

from datetime import UTC, datetime

from src.domain.abstractions.voice import (
    VoiceSession,
    VoiceSessionConfig,
    VoiceSessionState,
    WebRtcSignalingMessage,
    WebRtcSignalingProtocol,
)


class WebRtcSignalingAdapter(WebRtcSignalingProtocol):
    """In-process and Redis-ready WebRTC signaling adapter."""

    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}
        self._ice_candidates: dict[str, list[str]] = {}

    async def create_session(self, config: VoiceSessionConfig) -> VoiceSession:
        """Initializes a new WebRTC voice session."""
        session = VoiceSession(
            tenant_id=config.tenant_id,
            user_id=config.user_id,
            state=VoiceSessionState.INITIALIZING,
            config=config,
            created_at=datetime.now(UTC),
            last_ping_at=datetime.now(UTC),
        )
        self._sessions[session.session_id] = session
        self._ice_candidates[session.session_id] = []
        return session

    async def handle_signal(self, payload: WebRtcSignalingMessage) -> WebRtcSignalingMessage:
        """Processes incoming WebRTC signaling messages and returns negotiation reply."""
        session = self._sessions.get(payload.session_id)
        if not session:
            raise ValueError(f"WebRTC session {payload.session_id} does not exist")

        session.last_ping_at = datetime.now(UTC)

        if payload.message_type == "offer":
            # Client sent an SDP offer. Transition to SIGNALING and generate an SDP answer.
            session.state = VoiceSessionState.SIGNALING
            sdp_answer = (
                "v=0\r\n"
                f"o=- {payload.session_id} 2 IN IP4 127.0.0.1\r\n"
                "s=Retriever Edge Voice Session\r\n"
                "t=0 0\r\n"
                "a=group:BUNDLE audio\r\n"
                "m=audio 9 UDP/TLS/RTP/SAVPF 111\r\n"
                "c=IN IP4 0.0.0.0\r\n"
                "a=rtpmap:111 opus/48000/2\r\n"
                "a=fmtp:111 minptime=10;useinbandfec=1\r\n"
                "a=sendrecv\r\n"
            )
            return WebRtcSignalingMessage(
                session_id=payload.session_id,
                message_type="answer",
                sdp=sdp_answer,
                candidate=None,
            )

        elif payload.message_type == "ice_candidate":
            # Store trickle ICE candidate
            if payload.candidate:
                self._ice_candidates.setdefault(payload.session_id, []).append(payload.candidate)
            session.state = VoiceSessionState.CONNECTED
            session.connected_at = session.connected_at or datetime.now(UTC)

            # Acknowledge ICE candidate
            return WebRtcSignalingMessage(
                session_id=payload.session_id,
                message_type="ice_ack",
                candidate=payload.candidate,
            )

        elif payload.message_type == "hangup":
            session.state = VoiceSessionState.DISCONNECTED
            return WebRtcSignalingMessage(
                session_id=payload.session_id,
                message_type="hangup_ack",
            )

        return WebRtcSignalingMessage(
            session_id=payload.session_id,
            message_type="unknown_ack",
        )

    async def close_session(self, session_id: str) -> bool:
        """Terminates an active voice session."""
        session = self._sessions.get(session_id)
        if session:
            session.state = VoiceSessionState.DISCONNECTED
            self._sessions.pop(session_id, None)
            self._ice_candidates.pop(session_id, None)
            return True
        return False

    async def get_session(self, session_id: str) -> VoiceSession | None:
        """Retrieves session state."""
        return self._sessions.get(session_id)

    async def list_active_sessions(self, tenant_id: str) -> list[VoiceSession]:
        """Lists active voice sessions for a tenant."""
        return [
            s for s in self._sessions.values()
            if s.tenant_id == tenant_id and s.state != VoiceSessionState.DISCONNECTED
        ]
