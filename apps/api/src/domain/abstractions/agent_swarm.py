"""Domain abstractions for Multi-Agent Swarm Quorum & Dynamic Debate Consensus Engine (M109).

Conforms strictly to Hexagonal Architecture boundaries (0 framework or infrastructure imports).
Defines:
- SwarmAgentRole & SwarmAgentProfile
- DebateStance, CandidateClaim, DebateTurn, DebateRound
- AgentBallot, CandidateResolution
- QuorumConsensusResult & SwarmDebateRequest
- SwarmStats & SwarmDebateProtocol
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SwarmAgentRole(str, Enum):
    """Specialized cognitive roles in the collaborative agent swarm."""

    PLANNER = "planner"
    FORENSIC_AUDITOR = "forensic_auditor"
    CODE_SYNTHESIZER = "code_synthesizer"
    SKEPTIC_CRITIC = "skeptic_critic"


class DebateStance(str, Enum):
    """Dialectic stance adopted by an agent during a debate turn."""

    PROPOSAL = "proposal"
    CRITIQUE = "critique"
    REBUTTAL = "rebuttal"
    SYNTHESIS = "synthesis"


class SwarmAgentProfile(BaseModel):
    """Specification and operational configuration of a specialized swarm persona."""

    role: SwarmAgentRole
    display_name: str
    avatar_icon: str
    mandate: str
    base_weight: float = Field(default=1.0, ge=0.1, le=2.0)
    domain_tags: list[str] = Field(default_factory=list)
    model_tier: str = "frontier"


class CandidateClaim(BaseModel):
    """An individual assertion or hypothesis generated during debate rounds."""

    claim_id: str
    agent_role: SwarmAgentRole
    statement: str
    evidence_basis: list[str] = Field(default_factory=list)
    is_audited: bool = False
    is_verified: bool = True
    rejection_reason: str | None = None
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)


class DebateTurn(BaseModel):
    """A single atomic contribution within a dialectic debate round."""

    turn_index: int
    round_index: int
    agent_role: SwarmAgentRole
    stance: DebateStance
    content: str
    claims_proposed: list[CandidateClaim] = Field(default_factory=list)
    target_role: SwarmAgentRole | None = None
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    timestamp: float = Field(default_factory=time.time)


class DebateRound(BaseModel):
    """A complete structured dialectic debate stage."""

    round_index: int
    stage_name: str
    turns: list[DebateTurn] = Field(default_factory=list)
    round_summary: str = ""
    active_disagreements: list[str] = Field(default_factory=list)


class AgentBallot(BaseModel):
    """Formal confidence vote cast by a specialized agent on candidate resolutions."""

    agent_role: SwarmAgentRole
    candidate_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    weight: float = 1.0


class CandidateResolution(BaseModel):
    """A synthesized proposed solution evaluated during quorum voting."""

    resolution_id: str
    title: str
    detailed_solution: str
    supporting_roles: list[SwarmAgentRole] = Field(default_factory=list)
    weighted_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quorum_met: bool = False


class QuorumConsensusResult(BaseModel):
    """Complete result returned by the Multi-Agent Swarm Quorum Engine."""

    debate_id: str
    tenant_id: str
    prompt: str
    active_roles: list[SwarmAgentRole]
    rounds_completed: int
    rounds: list[DebateRound] = Field(default_factory=list)
    candidate_resolutions: list[CandidateResolution] = Field(default_factory=list)
    winning_consensus: str
    winning_resolution_id: str
    consensus_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    quorum_reached: bool = True
    quorum_threshold: float = 0.70
    hallucinations_pruned: list[CandidateClaim] = Field(default_factory=list)
    execution_time_ms: float
    created_at: float = Field(default_factory=time.time)


class SwarmDebateRequest(BaseModel):
    """Input specification to trigger a multi-agent dialectic debate."""

    tenant_id: str
    prompt: str = Field(..., min_length=1, description="High-stakes query or complex problem prompt")
    active_roles: list[SwarmAgentRole] | None = Field(
        default=None,
        description="Subset of specialized agent roles to participate (defaults to all 4)",
    )
    max_rounds: int = Field(default=3, ge=1, le=5, description="Maximum dialectic debate rounds")
    quorum_threshold: float = Field(
        default=0.70, ge=0.50, le=0.95, description="Minimum weighted confidence to reach quorum"
    )
    domain_context: str | None = Field(
        default=None, description="Optional grounding background or domain constraints"
    )


class SwarmStats(BaseModel):
    """Operational telemetry and aggregate statistics for swarm debates."""

    total_debates: int
    quorum_success_rate: float
    avg_debate_rounds: float
    total_hallucinations_pruned: int
    active_agent_count: int


class SwarmDebateEvent(BaseModel):
    """Event frame emitted over Server-Sent Events (SSE) stream during live debates."""

    event_type: str  # debate_start | round_start | agent_turn | peer_critique | ballot_cast | consensus_reached | error
    debate_id: str
    round_index: int | None = None
    agent_role: SwarmAgentRole | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)


class SwarmDebateProtocol(ABC):
    """Abstract interface for Multi-Agent Swarm Quorum Debate Engine."""

    @abstractmethod
    async def execute_debate(self, request: SwarmDebateRequest) -> QuorumConsensusResult:
        """Run full multi-round dialectic debate and return quorum consensus result."""
        ...

    @abstractmethod
    async def stream_debate(
        self, request: SwarmDebateRequest
    ) -> AsyncIterator[SwarmDebateEvent]:
        """Stream real-time debate turns and consensus ballots over async iterator."""
        ...

    @abstractmethod
    async def get_roles(self) -> list[SwarmAgentProfile]:
        """List all available specialized swarm agent roles."""
        ...

    @abstractmethod
    async def get_stats(self, tenant_id: str) -> SwarmStats:
        """Retrieve operational debate and quorum statistics."""
        ...
