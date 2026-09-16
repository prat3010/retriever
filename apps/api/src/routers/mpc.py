"""FastAPI Router for Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves (Milestone 121).

Exposes:
- Battery #36 operational health probe (`/v1/mpc/health`)
- MPC Privacy Enclave session lifecycle endpoints (`/v1/tenants/{tenantId}/mpc/sessions`)
- Sovereign party authentication and session joining (`.../join`)
- Additive vector share submission (`.../shares`)
- Confidential inner product execution & threshold Top-K retrieval (`.../compute`)
- Session results retrieval & differential privacy accounting (`.../results`)
- Session abortion (`.../abort`)
- Interactive mathematical Beaver triple and PPIP simulator (`/v1/mpc/math/simulate`)
"""

import logging

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import BaseModel, Field

from src.container import container
from src.domain.abstractions.mpc_enclave import (
    EnclavePartyRole,
    EncryptedVectorShare,
    MpcMathSimulationRequest,
    MpcMathSimulationResponse,
    MpcProtocolType,
    MpcResultsResponse,
    MpcSession,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Confidential MPC Privacy Enclaves"])


# --- Request/Response Models ---

class MpcHealthResponse(BaseModel):
    """Operational status and parameters for Platform Battery #36."""

    battery_id: str = "confidential_mpc_enclave"
    status: str = "healthy"
    category: str = "SAFETY_DEFENSE"
    milestone: str = "M121 (v2.0.0-alpha3)"
    supported_protocols: list[str] = Field(
        default_factory=lambda: ["additive_sharing", "beaver_triples", "shamir_threshold"]
    )
    fixed_point_scale: int = 65536
    default_privacy_threshold: float = 0.70
    latency_profile: str = "<12ms 2-party share protocol / <25ms 3-party Beaver inner product"
    zero_toy_verified: bool = True


class CreateMpcSessionRequest(BaseModel):
    """Payload to create an MPC Privacy Enclave session."""

    title: str = Field(..., min_length=3, description="Descriptive title of the collaborative query session")
    protocol: MpcProtocolType = Field(default=MpcProtocolType.BEAVER_TRIPLES, description="MPC protocol to execute")
    required_parties_count: int = Field(default=2, ge=2, le=10, description="Minimum participating parties required")
    dimension: int = Field(default=768, description="Vector dimension (e.g. 768, 1536)")
    privacy_threshold: float = Field(default=0.70, ge=0.0, le=1.0, description="Minimum cosine similarity cutoff")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum number of threshold matches to return")
    epsilon_budget: float = Field(default=10.0, ge=0.1, description="Total differential privacy budget for session")


class JoinMpcSessionRequest(BaseModel):
    """Payload for a sovereign party to join an MPC Enclave session."""

    party_id: str = Field(..., min_length=2, description="Unique party identifier (e.g. hospital_alpha)")
    display_name: str = Field(..., min_length=2, description="Human-readable organization or department name")
    public_key: str = Field(..., min_length=8, description="Party public key for share exchange")
    role: EnclavePartyRole = Field(default=EnclavePartyRole.EVALUATOR, description="Party role in session")


class SubmitVectorSharesRequest(BaseModel):
    """Payload for submitting quantized additive vector shares."""

    party_id: str = Field(..., description="Party submitting the shares")
    shares: list[EncryptedVectorShare] = Field(..., min_length=1, description="List of additive vector shares")


class AbortMpcSessionRequest(BaseModel):
    """Payload for aborting an active MPC session."""

    reason: str = Field(default="User initiated cancellation", description="Reason for abortion")


# --- Route Handlers ---

@router.get(
    "/v1/mpc/health",
    response_model=MpcHealthResponse,
    summary="Battery #36 Operational Health Probe",
)
def get_mpc_health() -> MpcHealthResponse:
    """Probe status, protocol options, and precision parameters for Battery #36."""
    return MpcHealthResponse()


@router.post(
    "/v1/tenants/{tenant_id}/mpc/sessions",
    response_model=MpcSession,
    status_code=status.HTTP_201_CREATED,
    summary="Create MPC Enclave Session",
)
def create_mpc_session(
    payload: CreateMpcSessionRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> MpcSession:
    """Provision a new collaborative Privacy Enclave session with specified threshold and parties."""
    adapter = container.mpc_enclave_adapter
    return adapter.create_session(
        tenant_id=tenant_id,
        title=payload.title,
        protocol=payload.protocol,
        required_parties_count=payload.required_parties_count,
        dimension=payload.dimension,
        privacy_threshold=payload.privacy_threshold,
        top_k=payload.top_k,
        epsilon_budget=payload.epsilon_budget,
    )


@router.get(
    "/v1/tenants/{tenant_id}/mpc/sessions",
    response_model=list[MpcSession],
    summary="List Tenant MPC Sessions",
)
def list_mpc_sessions(
    tenant_id: str = Path(..., description="Tenant identifier"),
) -> list[MpcSession]:
    """Retrieve all MPC sessions hosted by or joined by the tenant."""
    adapter = container.mpc_enclave_adapter
    return adapter.list_sessions(tenant_id)


@router.get(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}",
    response_model=MpcSession,
    summary="Get MPC Session Details",
)
def get_mpc_session(
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcSession:
    """Fetch status, participating parties, and lifecycle parameters of an MPC session."""
    adapter = container.mpc_enclave_adapter
    session = adapter.get_session(tenant_id, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MPC session '{session_id}' not found or inaccessible.",
        )
    return session


@router.post(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}/join",
    response_model=MpcSession,
    summary="Join MPC Session as Sovereign Party",
)
def join_mpc_session(
    payload: JoinMpcSessionRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcSession:
    """Register an authenticated sovereign party with public key into the MPC session."""
    adapter = container.mpc_enclave_adapter
    try:
        return adapter.join_session(
            tenant_id=tenant_id,
            session_id=session_id,
            party_id=payload.party_id,
            display_name=payload.display_name,
            public_key=payload.public_key,
            role=payload.role,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MPC session '{session_id}' not found.") from err
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}/shares",
    response_model=MpcSession,
    summary="Submit Additive Vector Shares",
)
def submit_vector_shares(
    payload: SubmitVectorSharesRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcSession:
    """Ingest encrypted or masked additive vector shares from a participating party."""
    adapter = container.mpc_enclave_adapter
    try:
        return adapter.submit_shares(
            tenant_id=tenant_id,
            session_id=session_id,
            party_id=payload.party_id,
            shares=payload.shares,
        )
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MPC session '{session_id}' not found.") from err
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@router.post(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}/compute",
    response_model=MpcResultsResponse,
    summary="Execute Confidential MPC Inner Product",
)
def execute_mpc_compute(
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcResultsResponse:
    """Execute Beaver triple multi-party inner product computation and return threshold Top-K matches."""
    adapter = container.mpc_enclave_adapter
    try:
        return adapter.execute_compute(tenant_id, session_id)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MPC session '{session_id}' not found.") from err
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}/results",
    response_model=MpcResultsResponse,
    summary="Get MPC Computation Results",
)
def get_mpc_results(
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcResultsResponse:
    """Retrieve verified Top-K results of an executed MPC session."""
    adapter = container.mpc_enclave_adapter
    results = adapter.get_results(tenant_id, session_id)
    if not results:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Results for MPC session '{session_id}' not available or not yet computed.",
        )
    return results


@router.post(
    "/v1/tenants/{tenant_id}/mpc/sessions/{session_id}/abort",
    response_model=MpcSession,
    summary="Abort MPC Session",
)
def abort_mpc_session(
    payload: AbortMpcSessionRequest,
    tenant_id: str = Path(..., description="Tenant identifier"),
    session_id: str = Path(..., description="Session identifier"),
) -> MpcSession:
    """Cancel and terminate an active MPC session."""
    adapter = container.mpc_enclave_adapter
    try:
        return adapter.abort_session(tenant_id, session_id, payload.reason)
    except KeyError as err:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"MPC session '{session_id}' not found.") from err


@router.post(
    "/v1/mpc/math/simulate",
    response_model=MpcMathSimulationResponse,
    summary="Simulate Beaver Triples & PPIP Math",
)
def simulate_mpc_math(
    request: MpcMathSimulationRequest,
) -> MpcMathSimulationResponse:
    """Evaluate authentic Additive Secret Sharing and Beaver Multiplication Triples mathematically."""
    adapter = container.mpc_enclave_adapter
    return adapter.simulate_mpc_math(request)
