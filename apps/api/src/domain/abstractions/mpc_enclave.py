"""Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves Domain Abstractions (Milestone 121).

Defines pure domain entities, cryptographic share representations, Beaver multiplication triple
data models, enclave session lifecycle states, and abstract port interfaces for collaborative
privacy-preserving vector similarity search. Contains strictly zero framework or infrastructure imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum

from pydantic import BaseModel, Field


class MpcProtocolType(StrEnum):
    """Supported multi-party computation cryptographic protocols."""

    ADDITIVE_SHARING = "additive_sharing"
    BEAVER_TRIPLES = "beaver_triples"
    SHAMIR_THRESHOLD = "shamir_threshold"


class EnclaveSessionStatus(StrEnum):
    """Lifecycle state machine for a confidential MPC privacy enclave session."""

    INITIALIZING = "initializing"
    KEY_EXCHANGE = "key_exchange"
    SHARES_INGESTED = "shares_ingested"
    COMPUTING = "computing"
    COMPLETED = "completed"
    ABORTED = "aborted"


class EnclavePartyRole(StrEnum):
    """Role of an authenticated sovereign party participating in an enclave."""

    INITIATOR = "initiator"
    EVALUATOR = "evaluator"
    OBSERVER = "observer"


class EnclaveParty(BaseModel):
    """An authenticated sovereign party participating in an MPC enclave."""

    party_id: str = Field(..., description="Unique party identifier (e.g. party_01)")
    tenant_id: str = Field(..., description="Sovereign tenant ID owning this party")
    display_name: str = Field(..., description="Human-readable organization or department name")
    role: EnclavePartyRole = Field(default=EnclavePartyRole.EVALUATOR, description="Party role in session")
    public_key: str = Field(..., description="Hex or base64 encoded public key for share encryption")
    has_submitted_shares: bool = Field(default=False, description="Whether this party has uploaded their shares")
    joined_at: str = Field(..., description="ISO 8601 timestamp of joining")


class EncryptedVectorShare(BaseModel):
    """An additive or polynomial secret share of a vector embedding."""

    share_id: str = Field(..., description="Unique identifier for the share")
    party_id: str = Field(..., description="Party submitting or holding this share")
    vector_id: str = Field(..., description="Identifier of the underlying document chunk or query")
    dimension: int = Field(..., description="Vector dimensionality (e.g. 768, 1536)")
    share_values: list[float] = Field(..., description="Quantized or masked additive shares")
    share_signature: str = Field(..., description="Cryptographic HMAC-SHA256 signature binding share to session")
    submitted_at: str = Field(..., description="ISO 8601 timestamp of submission")


class BeaverTripleDTO(BaseModel):
    """A pre-distributed correlated Beaver multiplication triple share for secure dot products."""

    triple_id: str = Field(..., description="Unique triple identifier")
    party_id: str = Field(..., description="Party assigned this triple slice")
    a_share: float = Field(..., description="Share of random scalar a: [a]_i")
    b_share: float = Field(..., description="Share of random scalar b: [b]_i")
    c_share: float = Field(..., description="Share of correlated product c = a * b: [c]_i")


class MpcSession(BaseModel):
    """Confidential Multi-Party Vector Computation Enclave Session."""

    session_id: str = Field(..., description="Unique UUID identifier for the MPC enclave session")
    tenant_id: str = Field(..., description="Sponsoring / host tenant identifier")
    title: str = Field(..., description="Descriptive title of the collaborative consortium query")
    protocol: MpcProtocolType = Field(default=MpcProtocolType.BEAVER_TRIPLES, description="Active MPC protocol")
    status: EnclaveSessionStatus = Field(default=EnclaveSessionStatus.INITIALIZING, description="Current lifecycle state")
    required_parties_count: int = Field(default=2, ge=2, description="Minimum parties required to compute")
    participating_parties: list[EnclaveParty] = Field(default_factory=list, description="Registered consortium parties")
    dimension: int = Field(default=768, description="Target vector dimension")
    fixed_point_scale: int = Field(default=65536, description="Fixed-point scaling factor (Q16.16)")
    privacy_threshold: float = Field(default=0.70, description="Minimum cosine similarity cutoff to reveal candidates")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of threshold matches to return")
    epsilon_budget_total: float = Field(default=10.0, description="Total differential privacy budget allocated")
    epsilon_budget_consumed: float = Field(default=0.0, description="Differential privacy budget expended to date")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    expires_at: str = Field(..., description="ISO 8601 expiration timestamp")


class MpcSimilarityResult(BaseModel):
    """A threshold-cleared confidential vector similarity result without raw coordinate leakage."""

    rank: int = Field(..., description="Rank position in Top-K (1-indexed)")
    item_id: str = Field(..., description="Matched document chunk identifier")
    owner_party_id: str = Field(..., description="Party that owns the matched candidate item")
    cosine_similarity: float = Field(..., description="Calculated joint cosine similarity score")
    passed_threshold: bool = Field(default=True, description="Whether similarity meets or exceeds privacy threshold")
    privacy_cost_epsilon: float = Field(default=0.25, description="Differential privacy budget consumed by this retrieval")


class MpcResultsResponse(BaseModel):
    """Final output of an executed confidential MPC vector similarity computation."""

    session_id: str = Field(..., description="Session identifier")
    status: EnclaveSessionStatus = Field(..., description="Session completion status")
    candidates_evaluated: int = Field(..., description="Total candidate pairs securely compared")
    matches_above_threshold: int = Field(..., description="Count of candidate items exceeding privacy threshold")
    results: list[MpcSimilarityResult] = Field(default_factory=list, description="Top-K privacy-filtered results")
    computation_time_ms: float = Field(..., description="Wall-clock execution time of MPC protocol in milliseconds")
    epsilon_remaining: float = Field(..., description="Remaining differential privacy budget for session")


class MpcMathSimulationRequest(BaseModel):
    """Input parameters for mathematical verification of Additive Secret Sharing and Beaver Triples."""

    vector_dimension: int = Field(default=8, ge=2, le=128, description="Vector dimension for simulation")
    parties_count: int = Field(default=3, ge=2, le=5, description="Number of sovereign parties in simulation")
    fixed_point_scale: int = Field(default=65536, description="Fixed-point scaling factor (e.g. 65536 for Q16.16)")
    query_vector: list[float] | None = Field(default=None, description="Optional custom query vector")
    candidate_vector: list[float] | None = Field(default=None, description="Optional custom candidate vector")


class MpcMathSimulationResponse(BaseModel):
    """Output results verifying the algebraic exactness of Additive Secret Sharing & Beaver Triples."""

    vector_dimension: int = Field(..., description="Evaluated vector dimension")
    parties_count: int = Field(..., description="Number of participating parties")
    plaintext_dot_product: float = Field(..., description="Standard floating-point inner product <q, d>")
    plaintext_cosine_similarity: float = Field(..., description="Standard floating-point cosine similarity")
    mpc_reconstructed_dot_product: float = Field(..., description="Dot product reconstructed from Beaver triples")
    mpc_cosine_similarity: float = Field(..., description="Cosine similarity calculated via confidential MPC")
    numerical_error_absolute: float = Field(..., description="Absolute difference between MPC and plaintext")
    shares_distribution_entropy: float = Field(..., description="Shannon entropy measuring share randomness")
    shares_sample: list[list[float]] = Field(..., description="First 3 coordinate shares for Party 1, Party 2, etc.")
    beaver_triples_verified: bool = Field(..., description="Whether Beaver multiplication relation c = a*b holds")


class MpcEnclavePort(ABC):
    """Abstract port for Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves."""

    @abstractmethod
    def create_session(
        self,
        tenant_id: str,
        title: str,
        protocol: MpcProtocolType,
        required_parties_count: int,
        dimension: int,
        privacy_threshold: float,
        top_k: int,
        epsilon_budget: float,
    ) -> MpcSession:
        """Create a new MPC enclave session."""

    @abstractmethod
    def get_session(self, tenant_id: str, session_id: str) -> MpcSession | None:
        """Fetch session by ID with tenant scope validation."""

    @abstractmethod
    def list_sessions(self, tenant_id: str) -> list[MpcSession]:
        """List all MPC sessions owned by or participating with tenant."""

    @abstractmethod
    def join_session(
        self,
        tenant_id: str,
        session_id: str,
        party_id: str,
        display_name: str,
        public_key: str,
        role: EnclavePartyRole,
    ) -> MpcSession:
        """Join a session as an authenticated sovereign party."""

    @abstractmethod
    def submit_shares(
        self,
        tenant_id: str,
        session_id: str,
        party_id: str,
        shares: list[EncryptedVectorShare],
    ) -> MpcSession:
        """Ingest additive vector shares from a participating party."""

    @abstractmethod
    def execute_compute(self, tenant_id: str, session_id: str) -> MpcResultsResponse:
        """Execute confidential inner product computation and threshold top-K filtering."""

    @abstractmethod
    def get_results(self, tenant_id: str, session_id: str) -> MpcResultsResponse | None:
        """Retrieve results of an executed session."""

    @abstractmethod
    def abort_session(self, tenant_id: str, session_id: str, reason: str) -> MpcSession:
        """Abort an active session."""

    @abstractmethod
    def simulate_mpc_math(self, request: MpcMathSimulationRequest) -> MpcMathSimulationResponse:
        """Pure mathematical simulation of secret sharing and Beaver triple inner products."""
