"""Tests for Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves (Milestone 121).

Validates:
- Authentic Additive Secret Sharing and exact vector reconstruction.
- Information-theoretic privacy & Shannon entropy of secret shares.
- Algebraic correctness of correlated Beaver multiplication triples (c = a * b).
- Bounded numerical error of Privacy-Preserving Inner Product (PPIP) vs plaintext dot product.
- Enclave session state machine lifecycle (INITIALIZING -> KEY_EXCHANGE -> SHARES_INGESTED -> COMPUTED).
- Multi-party threshold Top-K candidate pruning based on privacy threshold tau.
- Differential privacy budget (epsilon) tracking and depletion protection.
- FastAPI REST endpoints across health, session management, and mathematical simulation.
- Platform Battery #36 catalog registration in BatteryService.
- Hexagonal architecture boundary compliance.
"""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.adapters.security.mpc_enclave_adapter import (
    MpcEnclaveAdapter,
    calculate_beaver_inner_product,
    calculate_shannon_entropy,
    generate_additive_shares,
    generate_beaver_triples_for_dimension,
    normalize_vector,
    reconstruct_additive_shares,
)
from src.domain.abstractions.mpc_enclave import (
    EnclavePartyRole,
    EnclaveSessionStatus,
    EncryptedVectorShare,
    MpcProtocolType,
)
from src.domain.batteries.battery_service import BatteryCategory, BatteryService
from src.main import app


@pytest.fixture
def mpc_adapter() -> MpcEnclaveAdapter:
    return MpcEnclaveAdapter()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_additive_secret_sharing_exact_reconstruction() -> None:
    """Verify that vector split into N additive shares reconstructs with high precision."""
    vector = [0.25, -0.75, 0.50, 0.125, -0.333, 0.888]
    parties_count = 3
    scale = 65536

    shares = generate_additive_shares(vector, parties_count, scale=scale)
    assert len(shares) == parties_count
    assert len(shares[0]) == len(vector)

    reconstructed = reconstruct_additive_shares(shares)
    for orig, rec in zip(vector, reconstructed, strict=True):
        assert abs(orig - rec) < 1e-4


def test_shares_information_theoretic_privacy_and_entropy() -> None:
    """Ensure individual shares resemble uniform random noise with high entropy."""
    vector = [0.5] * 32
    shares = generate_additive_shares(vector, parties_count=3, scale=65536)

    # Party 1's shares should have high Shannon entropy and not reveal 0.5
    p1_coords = shares[0]
    entropy = calculate_shannon_entropy(p1_coords)
    assert entropy > 1.5
    # The shares should have high variance and not be constant or identical to original
    mean_val = sum(p1_coords) / len(p1_coords)
    variance = sum((c - mean_val) ** 2 for c in p1_coords) / len(p1_coords)
    assert variance > 0.05
    assert not all(abs(c - 0.5) < 0.01 for c in p1_coords)


def test_beaver_multiplication_triples_algebraic_correctness() -> None:
    """Verify that correlated Beaver triples satisfy c = a * b when reconstructed."""
    dim = 8
    parties_count = 3
    triples = generate_beaver_triples_for_dimension(dim, parties_count)

    for d in range(dim):
        a_val = sum(triples[p][d].a_share for p in range(parties_count))
        b_val = sum(triples[p][d].b_share for p in range(parties_count))
        c_val = sum(triples[p][d].c_share for p in range(parties_count))
        assert abs((a_val * b_val) - c_val) < 0.05


def test_beaver_inner_product_matches_plaintext() -> None:
    """Verify that Beaver triple PPIP computes dot product with bounded error."""
    dim = 16
    parties_count = 3
    q = normalize_vector([0.1 * i for i in range(dim)])
    d = normalize_vector([0.05 * (dim - i) for i in range(dim)])

    plaintext_dot = sum(q[i] * d[i] for i in range(dim))

    q_shares = generate_additive_shares(q, parties_count, scale=65536)
    d_shares = generate_additive_shares(d, parties_count, scale=65536)
    triples = generate_beaver_triples_for_dimension(dim, parties_count)

    mpc_dot = calculate_beaver_inner_product(q_shares, d_shares, triples)
    assert abs(mpc_dot - plaintext_dot) < 0.02


def test_mpc_session_lifecycle_and_joining(mpc_adapter: MpcEnclaveAdapter) -> None:
    """Verify session creation and state advancement upon parties joining."""
    session = mpc_adapter.create_session(
        tenant_id="tn_consortium_lead",
        title="Cross-Hospital Oncology Trial Discovery",
        protocol=MpcProtocolType.BEAVER_TRIPLES,
        required_parties_count=2,
        privacy_threshold=0.75,
    )
    assert session.status == EnclaveSessionStatus.INITIALIZING
    assert len(session.participating_parties) == 0

    # Party 1 joins
    mpc_adapter.join_session(
        tenant_id="tn_consortium_lead",
        session_id=session.session_id,
        party_id="party_hospital_a",
        display_name="St. Jude Research",
        public_key="0xABCDEF1234567890",
        role=EnclavePartyRole.INITIATOR,
    )
    updated = mpc_adapter.get_session("tn_consortium_lead", session.session_id)
    assert updated is not None
    assert len(updated.participating_parties) == 1
    assert updated.status == EnclaveSessionStatus.INITIALIZING

    # Party 2 joins (satisfies required_parties_count=2)
    mpc_adapter.join_session(
        tenant_id="tn_hospital_b",
        session_id=session.session_id,
        party_id="party_hospital_b",
        display_name="Mayo Clinic AI",
        public_key="0xFEDCBA0987654321",
        role=EnclavePartyRole.EVALUATOR,
    )
    ready = mpc_adapter.get_session("tn_consortium_lead", session.session_id)
    assert ready is not None
    assert len(ready.participating_parties) == 2
    assert ready.status == EnclaveSessionStatus.KEY_EXCHANGE


def test_mpc_shares_ingestion_and_computation(mpc_adapter: MpcEnclaveAdapter) -> None:
    """Verify share submission, status advancement, and Top-K threshold filtering."""
    session = mpc_adapter.create_session(
        tenant_id="tn_defense_lead",
        title="Joint Supply Chain Vulnerability Scan",
        required_parties_count=2,
        privacy_threshold=0.70,
        top_k=3,
        epsilon_budget=5.0,
    )

    mpc_adapter.join_session(
        tenant_id="tn_defense_lead",
        session_id=session.session_id,
        party_id="contractor_alpha",
        display_name="Alpha Dynamics",
        public_key="0xAAAA1111",
        role=EnclavePartyRole.INITIATOR,
    )
    mpc_adapter.join_session(
        tenant_id="tn_defense_sub",
        session_id=session.session_id,
        party_id="contractor_beta",
        display_name="Beta Systems",
        public_key="0xBBBB2222",
        role=EnclavePartyRole.EVALUATOR,
    )

    # Submit shares for party 1
    dummy_share_1 = EncryptedVectorShare(
        share_id="sh_alpha_01",
        party_id="contractor_alpha",
        vector_id="query_supply_chain",
        dimension=session.dimension,
        share_values=[0.1] * session.dimension,
        share_signature="sig_alpha",
        submitted_at="2026-09-16T00:00:00Z",
    )
    mpc_adapter.submit_shares(
        tenant_id="tn_defense_lead",
        session_id=session.session_id,
        party_id="contractor_alpha",
        shares=[dummy_share_1],
    )

    # Submit shares for party 2
    dummy_share_2 = EncryptedVectorShare(
        share_id="sh_beta_01",
        party_id="contractor_beta",
        vector_id="query_supply_chain",
        dimension=session.dimension,
        share_values=[0.2] * session.dimension,
        share_signature="sig_beta",
        submitted_at="2026-09-16T00:00:00Z",
    )
    mpc_adapter.submit_shares(
        tenant_id="tn_defense_sub",
        session_id=session.session_id,
        party_id="contractor_beta",
        shares=[dummy_share_2],
    )

    ingested = mpc_adapter.get_session("tn_defense_lead", session.session_id)
    assert ingested is not None
    assert ingested.status == EnclaveSessionStatus.SHARES_INGESTED

    # Execute compute
    results = mpc_adapter.execute_compute("tn_defense_lead", session.session_id)
    assert results.status == EnclaveSessionStatus.COMPLETED
    assert results.candidates_evaluated > 0
    assert len(results.results) <= session.top_k
    # Ensure all results meet or exceed privacy threshold
    for r in results.results:
        assert r.cosine_similarity >= session.privacy_threshold
        assert r.passed_threshold is True

    # Differential privacy budget was consumed
    assert results.epsilon_remaining < 5.0


def test_mpc_privacy_budget_depletion_protection(mpc_adapter: MpcEnclaveAdapter) -> None:
    """Verify that depleted privacy budget halts further computations."""
    session = mpc_adapter.create_session(
        tenant_id="tn_budget_test",
        title="Tight Budget Session",
        epsilon_budget=0.40,  # lower than single query cost 0.50
    )
    mpc_adapter.join_session(
        tenant_id="tn_budget_test",
        session_id=session.session_id,
        party_id="p1",
        display_name="P1",
        public_key="0x111",
    )
    mpc_adapter.join_session(
        tenant_id="tn_budget_test",
        session_id=session.session_id,
        party_id="p2",
        display_name="P2",
        public_key="0x222",
    )

    with pytest.raises(ValueError, match="Differential privacy budget exceeded"):
        mpc_adapter.execute_compute("tn_budget_test", session.session_id)


def test_fastapi_mpc_endpoints(client: TestClient) -> None:
    """Test full FastAPI endpoint suite for Battery #36."""
    # 1. Health probe
    health_resp = client.get("/v1/mpc/health")
    assert health_resp.status_code == 200
    data = health_resp.json()
    assert data["battery_id"] == "confidential_mpc_enclave"
    assert data["status"] == "healthy"
    assert "beaver_triples" in data["supported_protocols"]

    # 2. Math simulation endpoint
    sim_resp = client.post(
        "/v1/mpc/math/simulate",
        json={"vector_dimension": 8, "parties_count": 3, "fixed_point_scale": 65536},
    )
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert sim_data["beaver_triples_verified"] is True
    assert sim_data["numerical_error_absolute"] < 0.05
    assert sim_data["shares_distribution_entropy"] > 1.0

    # 3. Create session via REST
    create_resp = client.post(
        "/v1/tenants/tn_rest_consortium/mpc/sessions",
        json={
            "title": "REST API Consortium Search",
            "protocol": "beaver_triples",
            "required_parties_count": 2,
            "dimension": 768,
            "privacy_threshold": 0.70,
            "top_k": 5,
        },
    )
    assert create_resp.status_code == 201
    sess_data = create_resp.json()
    sess_id = sess_data["session_id"]

    # 4. List sessions
    list_resp = client.get("/v1/tenants/tn_rest_consortium/mpc/sessions")
    assert list_resp.status_code == 200
    assert any(s["session_id"] == sess_id for s in list_resp.json())

    # 5. Join session
    join_resp = client.post(
        f"/v1/tenants/tn_rest_consortium/mpc/sessions/{sess_id}/join",
        json={
            "party_id": "rest_party_01",
            "display_name": "Partner Bank A",
            "public_key": "0x99887766",
            "role": "initiator",
        },
    )
    assert join_resp.status_code == 200
    assert len(join_resp.json()["participating_parties"]) == 1


def test_battery_36_registration() -> None:
    """Ensure confidential_mpc_enclave is properly registered in BatteryService."""
    service = BatteryService()
    resp = service.get_platform_batteries()
    battery = next((b for b in resp.batteries if b.id == "confidential_mpc_enclave"), None)
    assert battery is not None
    assert battery.name == "Confidential Multi-Party Vector Computation (MPC) Privacy Enclaves"
    assert battery.category == BatteryCategory.SAFETY_DEFENSE
    assert "M121" in battery.milestone
    assert battery.health_check_endpoint == "/v1/mpc/health"


def test_hexagonal_architecture_domain_isolation() -> None:
    """Verify that mpc_enclave domain abstraction imports zero infrastructure frameworks."""
    domain_file = Path(__file__).resolve().parent.parent / "src/domain/abstractions/mpc_enclave.py"
    assert domain_file.exists(), f"Domain file not found: {domain_file}"
    tree = ast.parse(domain_file.read_text(encoding="utf-8"))

    forbidden_modules = {"fastapi", "sqlalchemy", "redis", "pydantic_settings", "httpx", "requests"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert root_pkg not in forbidden_modules, f"Forbidden import '{root_pkg}' in pure domain"
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_pkg = node.module.split(".")[0]
            assert root_pkg not in forbidden_modules, f"Forbidden import '{root_pkg}' in pure domain"
