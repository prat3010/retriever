"""Tests for Enterprise Identity Federation (SAML 2.0 / SCIM 2.0) & RB-VAC (M119, Battery #34)."""

import base64
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from httpx import ASGITransport, AsyncClient

from src.container import battery_service, identity_federation_adapter
from src.domain.abstractions.batteries import BatteryStatus
from src.domain.abstractions.identity_federation import (
    AccessControlContext,
    RbVacCandidateChunk,
    SamlIdpConfig,
)
from src.main import app


@pytest.fixture
def test_tenant_id() -> str:
    return "tn_enterprise_corp_99"


@pytest.fixture(scope="session")
def saml_test_key_and_cert():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "idp.okta.com")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return key, cert_pem


def sign_saml_response(raw_xml: str, private_key: rsa.RSAPrivateKey) -> str:
    ET.register_namespace("ds", "http://www.w3.org/2000/09/xmldsig#")
    ET.register_namespace("saml", "urn:oasis:names:tc:SAML:2.0:assertion")
    ET.register_namespace("samlp", "urn:oasis:names:tc:SAML:2.0:protocol")

    root = ET.fromstring(raw_xml)
    assertion = root.find(".//{urn:oasis:names:tc:SAML:2.0:assertion}Assertion")
    if assertion is None:
        raise ValueError("Assertion not found in XML")
    assertion_id = assertion.get("ID", "_assert_default")

    c14n_assertion = ET.canonicalize(ET.tostring(assertion))
    hasher = hashes.Hash(hashes.SHA256())
    hasher.update(c14n_assertion.encode("utf-8"))
    digest = base64.b64encode(hasher.finalize()).decode("utf-8")

    signed_info_xml = f"""<ds:SignedInfo xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
<ds:CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
<ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
<ds:Reference URI="#{assertion_id}">
<ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
<ds:DigestValue>{digest}</ds:DigestValue>
</ds:Reference>
</ds:SignedInfo>"""

    c14n_si = ET.canonicalize(signed_info_xml)
    sig_bytes = private_key.sign(c14n_si.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

    sig_xml = f"""<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
{signed_info_xml}
<ds:SignatureValue>{sig_b64}</ds:SignatureValue>
</ds:Signature>"""

    assertion.append(ET.fromstring(sig_xml))
    return ET.tostring(root, encoding="utf-8").decode("utf-8")


@pytest.fixture
def sample_saml_xml() -> str:
    now = datetime.now(UTC)
    not_after = (now + timedelta(hours=1)).isoformat()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                ID="_resp_12345" Version="2.0">
  <saml:Issuer>https://idp.okta.com/exk12345</saml:Issuer>
  <saml:Assertion ID="_assert_67890" Version="2.0">
    <saml:Issuer>https://idp.okta.com/exk12345</saml:Issuer>
    <saml:Subject>
      <saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">
        lead_engineer@enterprise.internal
      </saml:NameID>
    </saml:Subject>
    <saml:Conditions NotBefore="{now.isoformat()}" NotOnOrAfter="{not_after}">
      <saml:AudienceRestriction>
        <saml:Audience>http://localhost:8000/saml</saml:Audience>
      </saml:AudienceRestriction>
    </saml:Conditions>
    <saml:AttributeStatement>
      <saml:Attribute Name="firstName">
        <saml:AttributeValue>Alex</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="lastName">
        <saml:AttributeValue>Vance</saml:AttributeValue>
      </saml:Attribute>
      <saml:Attribute Name="groups">
        <saml:AttributeValue>engineering</saml:AttributeValue>
        <saml:AttributeValue>devops</saml:AttributeValue>
      </saml:Attribute>
    </saml:AttributeStatement>
  </saml:Assertion>
</samlp:Response>"""


@pytest.mark.asyncio
async def test_saml_configuration_and_sp_metadata(test_tenant_id: str):
    """Verify SAML IdP configuration persistence and standard SP metadata XML generation."""
    config = SamlIdpConfig(
        tenant_id=test_tenant_id,
        idp_entity_id="https://idp.okta.com/exk12345",
        sso_url="https://idp.okta.com/exk12345/sso/saml",
        idp_x509_cert="MIIDpjCCAo6gAwIBAgIGAY...==",
        sp_entity_id="http://localhost:8000/saml",
        default_groups=["all_staff"],
    )

    saved = await identity_federation_adapter.configure_saml_idp(config)
    assert saved.tenant_id == test_tenant_id
    assert saved.enabled is True

    retrieved = await identity_federation_adapter.get_saml_idp_config(test_tenant_id)
    assert retrieved is not None
    assert retrieved.idp_entity_id == "https://idp.okta.com/exk12345"

    sp_xml = await identity_federation_adapter.generate_sp_metadata(test_tenant_id)
    assert "<md:EntityDescriptor" in sp_xml
    assert 'entityID="http://localhost:8000/saml"' in sp_xml
    assert "AssertionConsumerService" in sp_xml


@pytest.mark.asyncio
async def test_saml_assertion_validation(
    test_tenant_id: str, sample_saml_xml: str, saml_test_key_and_cert
):
    """Verify cryptographic SAML assertion attribute extraction, signature verification, and security group mapping."""
    key, cert_pem = saml_test_key_and_cert
    config = SamlIdpConfig(
        tenant_id=test_tenant_id,
        idp_entity_id="https://idp.okta.com/exk12345",
        sso_url="https://idp.okta.com/exk12345/sso/saml",
        idp_x509_cert=cert_pem,
        default_groups=["all_staff"],
    )
    await identity_federation_adapter.configure_saml_idp(config)

    signed_xml = sign_saml_response(sample_saml_xml, key)
    b64_xml = base64.b64encode(signed_xml.encode("utf-8")).decode("utf-8")
    payload = await identity_federation_adapter.process_saml_response(test_tenant_id, b64_xml)

    assert payload.name_id == "lead_engineer@enterprise.internal"
    assert "engineering" in payload.security_groups
    assert "devops" in payload.security_groups
    assert "all_staff" in payload.security_groups
    assert payload.attributes.get("firstName") == "Alex"
    assert payload.is_verified is True


@pytest.mark.asyncio
async def test_saml_unsigned_assertion_rejected(test_tenant_id: str, sample_saml_xml: str, saml_test_key_and_cert):
    """Verify unsigned SAML assertions are rejected when IdP certificate is configured."""
    _, cert_pem = saml_test_key_and_cert
    config = SamlIdpConfig(
        tenant_id=test_tenant_id,
        idp_entity_id="https://idp.okta.com/exk12345",
        sso_url="https://idp.okta.com/exk12345/sso/saml",
        idp_x509_cert=cert_pem,
        default_groups=["all_staff"],
    )
    await identity_federation_adapter.configure_saml_idp(config)

    # Unsigned XML
    b64_xml = base64.b64encode(sample_saml_xml.encode("utf-8")).decode("utf-8")
    with pytest.raises(ValueError, match="missing required XMLDSig Signature"):
        await identity_federation_adapter.process_saml_response(test_tenant_id, b64_xml)


@pytest.mark.asyncio
async def test_saml_tampered_assertion_rejected(test_tenant_id: str, sample_saml_xml: str, saml_test_key_and_cert):
    """Verify tampered SAML assertions fail cryptographic signature verification."""
    key, cert_pem = saml_test_key_and_cert
    config = SamlIdpConfig(
        tenant_id=test_tenant_id,
        idp_entity_id="https://idp.okta.com/exk12345",
        sso_url="https://idp.okta.com/exk12345/sso/saml",
        idp_x509_cert=cert_pem,
        default_groups=["all_staff"],
    )
    await identity_federation_adapter.configure_saml_idp(config)

    signed_xml = sign_saml_response(sample_saml_xml, key)
    # Tamper with NameID after signing
    tampered_xml = signed_xml.replace("lead_engineer@enterprise.internal", "attacker@evil.com")
    b64_xml = base64.b64encode(tampered_xml.encode("utf-8")).decode("utf-8")

    with pytest.raises(ValueError, match="(signature verification failed|digest mismatch)"):
        await identity_federation_adapter.process_saml_response(test_tenant_id, b64_xml)


@pytest.mark.asyncio
async def test_saml_expired_assertion(test_tenant_id: str, saml_test_key_and_cert):
    """Verify expired SAML assertions raise security validation error."""
    key, cert_pem = saml_test_key_and_cert
    config = SamlIdpConfig(
        tenant_id=test_tenant_id,
        idp_entity_id="https://idp.okta.com/exk12345",
        sso_url="https://idp.okta.com/exk12345/sso/saml",
        idp_x509_cert=cert_pem,
        default_groups=["all_staff"],
    )
    await identity_federation_adapter.configure_saml_idp(config)

    past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    expired_xml = f"""<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
      <saml:Issuer>https://idp.okta.com/exk12345</saml:Issuer>
      <saml:Assertion ID="_exp" Version="2.0">
        <saml:Issuer>https://idp.okta.com/exk12345</saml:Issuer>
        <saml:Subject><saml:NameID>test@domain.com</saml:NameID></saml:Subject>
        <saml:Conditions NotOnOrAfter="{past}" />
      </saml:Assertion>
    </samlp:Response>"""
    signed_expired_xml = sign_saml_response(expired_xml, key)
    b64_xml = base64.b64encode(signed_expired_xml.encode("utf-8")).decode("utf-8")

    with pytest.raises(ValueError, match="expired"):
        await identity_federation_adapter.process_saml_response(test_tenant_id, b64_xml)


@pytest.mark.asyncio
async def test_scim_user_lifecycle(test_tenant_id: str):
    """Verify RFC 7644 SCIM 2.0 User provisioning, retrieval, patching, and deprovisioning."""
    # 1. Token generation
    token = await identity_federation_adapter.generate_scim_token(test_tenant_id)
    assert token.startswith("scim_live_")

    # 2. Create User
    new_user_payload = {
        "userName": "sarah.connor@enterprise.internal",
        "displayName": "Sarah Connor",
        "active": True,
        "emails": [{"value": "sarah.connor@enterprise.internal", "primary": True}],
    }
    user = await identity_federation_adapter.create_scim_user(test_tenant_id, new_user_payload)
    assert user.id.startswith("usr_")
    assert user.userName == "sarah.connor@enterprise.internal"
    assert user.active is True

    # 3. Get User
    fetched = await identity_federation_adapter.get_scim_user(test_tenant_id, user.id)
    assert fetched is not None
    assert fetched.id == user.id

    # 4. List Users with filter
    list_res = await identity_federation_adapter.list_scim_users(
        test_tenant_id, filter_query='userName eq "sarah.connor@enterprise.internal"'
    )
    assert list_res.totalResults == 1
    assert list_res.Resources[0].id == user.id

    # 5. Patch User (Deprovisioning)
    patched = await identity_federation_adapter.patch_scim_user(
        test_tenant_id,
        user.id,
        operations=[{"op": "replace", "path": "active", "value": False}],
    )
    assert patched.active is False

    # 6. Delete User
    deleted = await identity_federation_adapter.delete_scim_user(test_tenant_id, user.id)
    assert deleted is True
    assert await identity_federation_adapter.get_scim_user(test_tenant_id, user.id) is None


@pytest.mark.asyncio
async def test_scim_group_lifecycle(test_tenant_id: str):
    """Verify RFC 7644 SCIM 2.0 Group creation, membership patching, and removal."""
    group_payload = {
        "displayName": "Cybersecurity Response",
        "members": [{"value": "usr_001", "display": "Security Analyst"}],
    }
    group = await identity_federation_adapter.create_scim_group(test_tenant_id, group_payload)
    assert group.id.startswith("grp_")
    assert group.displayName == "Cybersecurity Response"
    assert len(group.members) == 1

    # Add member via PATCH
    patched = await identity_federation_adapter.patch_scim_group(
        test_tenant_id,
        group.id,
        operations=[{"op": "add", "value": [{"value": "usr_002", "display": "Threat Hunter"}]}],
    )
    assert len(patched.members) == 2

    # Remove member via PATCH
    patched_del = await identity_federation_adapter.patch_scim_group(
        test_tenant_id,
        group.id,
        operations=[{"op": "remove", "value": ["usr_001"]}],
    )
    assert len(patched_del.members) == 1
    assert patched_del.members[0].value == "usr_002"

    # Delete Group
    deleted = await identity_federation_adapter.delete_scim_group(test_tenant_id, group.id)
    assert deleted is True
    assert await identity_federation_adapter.get_scim_group(test_tenant_id, group.id) is None


@pytest.mark.asyncio
async def test_rbvac_retrieval_filtering(test_tenant_id: str):
    """Verify Role-Based Vector Access Control pre-retrieval filtering blocks unauthorized chunks."""
    candidates = [
        RbVacCandidateChunk(
            chunk_id="chk_pub_01",
            document_id="doc_handbook",
            content="Public company overview and office address.",
            score=0.95,
            acl_groups=["*"],
            classification="public",
        ),
        RbVacCandidateChunk(
            chunk_id="chk_eng_02",
            document_id="doc_backend_infra",
            content="API gateway rate limits and database sharding keys.",
            score=0.91,
            acl_groups=["engineering"],
            classification="internal",
        ),
        RbVacCandidateChunk(
            chunk_id="chk_fin_03",
            document_id="doc_board_salaries",
            content="Executive leadership compensation and severance packages.",
            score=0.96,
            acl_groups=["finance", "executive"],
            classification="restricted",
        ),
    ]

    # 1. Junior Engineer (holds 'engineering' badge only)
    eng_ctx = AccessControlContext(
        user_id="usr_eng_1",
        tenant_id=test_tenant_id,
        email="eng@enterprise.internal",
        security_groups=["engineering"],
    )
    eng_res = await identity_federation_adapter.enforce_rbvac(test_tenant_id, eng_ctx, candidates)
    assert len(eng_res.allowed_candidates) == 2
    assert len(eng_res.pruned_telemetry) == 1
    assert eng_res.pruned_telemetry[0].chunk_id == "chk_fin_03"
    assert "Insufficient security group clearance" in eng_res.pruned_telemetry[0].reason

    # 2. CFO (holds 'finance' badge)
    cfo_ctx = AccessControlContext(
        user_id="usr_cfo_1",
        tenant_id=test_tenant_id,
        email="cfo@enterprise.internal",
        security_groups=["finance"],
    )
    cfo_res = await identity_federation_adapter.enforce_rbvac(test_tenant_id, cfo_ctx, candidates)
    # CFO has clearance for public and finance chunks
    assert len(cfo_res.allowed_candidates) == 2
    allowed_ids = {c.chunk_id for c in cfo_res.allowed_candidates}
    assert "chk_pub_01" in allowed_ids
    assert "chk_fin_03" in allowed_ids
    assert len(cfo_res.pruned_telemetry) == 1
    assert cfo_res.pruned_telemetry[0].chunk_id == "chk_eng_02"


@pytest.mark.asyncio
async def test_fastapi_identity_endpoints(test_tenant_id: str):
    """Verify FastAPI routes for identity health, SAML, SCIM, and RB-VAC simulation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health Probe
        h_res = await client.get("/v1/identity/health")
        assert h_res.status_code == 200
        data = h_res.json()
        assert data["battery_id"] == "enterprise_identity_federation"
        assert data["status"] == "healthy"

        # 2. SCIM Discovery Endpoints
        sp_res = await client.get("/v1/scim/v2/ServiceProviderConfig")
        assert sp_res.status_code == 200
        assert sp_res.json()["patch"]["supported"] is True

        schema_res = await client.get("/v1/scim/v2/Schemas")
        assert schema_res.status_code == 200
        assert schema_res.json()["totalResults"] == 2

        # 3. SCIM Token Issuance
        tok_res = await client.post(f"/v1/tenants/{test_tenant_id}/identity/scim/token")
        assert tok_res.status_code == 200
        assert "scim_live_" in tok_res.json()["token"]

        # 4. RB-VAC Simulation Route
        sim_res = await client.post(
            f"/v1/tenants/{test_tenant_id}/identity/rbvac/simulate",
            json={
                "user_id": "usr_intern_01",
                "email": "intern@corp.local",
                "security_groups": ["sales"],
            },
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["total_candidates"] == 4
        # Public handbook allowed, engineering/finance/executive pruned
        assert len(sim_data["allowed_candidates"]) == 1
        assert len(sim_data["pruned_telemetry"]) == 3


@pytest.mark.asyncio
async def test_battery_34_registration():
    """Verify Platform Battery #34 is cataloged in BatteryService under SAFETY_DEFENSE."""
    b = battery_service.get_battery("enterprise_identity_federation")
    assert b is not None
    assert b.id == "enterprise_identity_federation"
    assert b.category.value == "safety_defense"
    assert b.status == BatteryStatus.ACTIVE
    assert "M119" in b.milestone
    assert b.health_check_endpoint == "/v1/identity/health"
