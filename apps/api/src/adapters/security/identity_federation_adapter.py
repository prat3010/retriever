import base64
import copy
import secrets
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from src.domain.abstractions.identity_federation import (
    AccessControlContext,
    IdentityFederationPort,
    RbVacCandidateChunk,
    RbVacPrunedTelemetry,
    RbVacSimulationResult,
    SamlAssertionPayload,
    SamlIdpConfig,
    ScimEmail,
    ScimGroup,
    ScimGroupMember,
    ScimListResponse,
    ScimMeta,
    ScimUser,
)


class IdentityFederationAdapter(IdentityFederationPort):
    """Adapter for SAML 2.0 SSO, SCIM 2.0 directory lifecycle, and RB-VAC."""

    def __init__(self) -> None:
        self._saml_configs: dict[str, SamlIdpConfig] = {}
        self._scim_tokens: dict[str, str] = {}
        # Multi-tenant SCIM storage: tenant_id -> {id -> ScimUser / ScimGroup}
        self._users: dict[str, dict[str, ScimUser]] = {}
        self._groups: dict[str, dict[str, ScimGroup]] = {}

    def _ensure_tenant_storage(self, tenant_id: str) -> None:
        if tenant_id not in self._users:
            self._users[tenant_id] = {}
        if tenant_id not in self._groups:
            self._groups[tenant_id] = {}
            # Initialize default corporate security groups
            now = datetime.now(UTC).isoformat()
            default_groups = [
                ("grp_all_staff", "All Staff", []),
                ("grp_eng", "Engineering", []),
                ("grp_fin", "Finance & Accounting", []),
                ("grp_exec", "Executive Board", []),
            ]
            for g_id, g_name, g_members in default_groups:
                self._groups[tenant_id][g_id] = ScimGroup(
                    id=g_id,
                    displayName=g_name,
                    members=[
                        ScimGroupMember(value=m, display=m) for m in g_members
                    ],
                    meta=ScimMeta(
                        resourceType="Group",
                        created=now,
                        lastModified=now,
                        location=f"/v1/scim/v2/tenants/{tenant_id}/Groups/{g_id}",
                    ),
                )

    async def configure_saml_idp(self, config: SamlIdpConfig) -> SamlIdpConfig:
        now = datetime.now(UTC).isoformat()
        if not config.created_at:
            config.created_at = now
        config.updated_at = now
        self._saml_configs[config.tenant_id] = config
        self._ensure_tenant_storage(config.tenant_id)
        return config

    async def get_saml_idp_config(self, tenant_id: str) -> SamlIdpConfig | None:
        return self._saml_configs.get(tenant_id)

    async def generate_sp_metadata(self, tenant_id: str) -> str:
        config = self._saml_configs.get(tenant_id)
        sp_entity_id = config.sp_entity_id if config else "http://localhost:8000/saml"
        acs_url = (
            config.acs_url
            if config
            else f"http://localhost:8000/v1/identity/saml/acs?tenant={tenant_id}"
        )

        metadata_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata" '
            f'entityID="{sp_entity_id}">\n'
            '  <md:SPSSODescriptor AuthnRequestsSigned="false" WantAssertionsSigned="true" '
            'protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">\n'
            '    <md:NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</md:NameIDFormat>\n'
            f'    <md:AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
            f'Location="{acs_url}" index="1" isDefault="true"/>\n'
            '  </md:SPSSODescriptor>\n'
            '</md:EntityDescriptor>'
        )
        return metadata_xml

    def _verify_saml_signature(self, root: ET.Element, cert_pem_or_der: str) -> bool:
        """Verify XML Digital Signature (XMLDSig) over SAML response/assertion against IdP certificate."""
        ds_ns = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
        sig_node = root.find(".//ds:Signature", ds_ns)
        if sig_node is None:
            raise ValueError("SAML response is missing required XMLDSig Signature")

        si_node = sig_node.find("ds:SignedInfo", ds_ns)
        sig_val_node = sig_node.find("ds:SignatureValue", ds_ns)
        if si_node is None or sig_val_node is None or not sig_val_node.text:
            raise ValueError("SAML signature is malformed: missing SignedInfo or SignatureValue")

        # 1. Load Certificate
        clean_cert = cert_pem_or_der.strip()
        try:
            if "-----BEGIN CERTIFICATE-----" in clean_cert:
                cert = x509.load_pem_x509_certificate(clean_cert.encode("utf-8"))
            else:
                pem_formatted = f"-----BEGIN CERTIFICATE-----\n{clean_cert}\n-----END CERTIFICATE-----"
                try:
                    cert = x509.load_pem_x509_certificate(pem_formatted.encode("utf-8"))
                except Exception:
                    cert = x509.load_der_x509_certificate(base64.b64decode(clean_cert))
        except Exception as err:
            raise ValueError(f"Invalid IdP X.509 certificate: {err}") from err

        # 2. Canonicalize SignedInfo and verify RSA signature
        ET.register_namespace("ds", "http://www.w3.org/2000/09/xmldsig#")
        ET.register_namespace("saml", "urn:oasis:names:tc:SAML:2.0:assertion")
        ET.register_namespace("samlp", "urn:oasis:names:tc:SAML:2.0:protocol")

        c14n_signed_info = ET.canonicalize(ET.tostring(si_node))
        sig_bytes = base64.b64decode(sig_val_node.text.strip())

        sig_method_node = si_node.find("ds:SignatureMethod", ds_ns)
        sig_algo = sig_method_node.get("Algorithm", "").lower() if sig_method_node is not None else ""
        if "sha1" in sig_algo:
            hash_algo = hashes.SHA1()
        elif "sha384" in sig_algo:
            hash_algo = hashes.SHA384()
        elif "sha512" in sig_algo:
            hash_algo = hashes.SHA512()
        else:
            hash_algo = hashes.SHA256()

        try:
            cert.public_key().verify(
                sig_bytes,
                c14n_signed_info.encode("utf-8"),
                padding.PKCS1v15(),
                hash_algo,
            )
        except Exception as err:
            raise ValueError(f"SAML XMLDSig signature verification failed: {err}") from err

        # 3. Verify Reference digest if present
        ref_node = si_node.find("ds:Reference", ds_ns)
        if ref_node is not None:
            digest_val_node = ref_node.find("ds:DigestValue", ds_ns)
            if digest_val_node is not None and digest_val_node.text:
                expected_digest = digest_val_node.text.strip()
                uri = ref_node.get("URI", "").lstrip("#")
                target_el = root.find(f".//*[@ID='{uri}']") if uri else root
                if target_el is not None:
                    target_copy = copy.deepcopy(target_el)
                    sig_in_target = target_copy.find(".//ds:Signature", ds_ns)
                    if sig_in_target is not None:
                        for parent in target_copy.iter():
                            if sig_in_target in list(parent):
                                parent.remove(sig_in_target)
                                break
                    c14n_target = ET.canonicalize(ET.tostring(target_copy))
                    digest_method_node = ref_node.find("ds:DigestMethod", ds_ns)
                    digest_algo = (
                        digest_method_node.get("Algorithm", "").lower()
                        if digest_method_node is not None
                        else ""
                    )
                    if "sha1" in digest_algo:
                        d_hash = hashes.SHA1()
                    elif "sha384" in digest_algo:
                        d_hash = hashes.SHA384()
                    elif "sha512" in digest_algo:
                        d_hash = hashes.SHA512()
                    else:
                        d_hash = hashes.SHA256()
                    hasher = hashes.Hash(d_hash)
                    hasher.update(c14n_target.encode("utf-8"))
                    actual_digest = base64.b64encode(hasher.finalize()).decode("utf-8")
                    if actual_digest != expected_digest:
                        raise ValueError(
                            f"SAML reference digest mismatch (expected {expected_digest}, computed {actual_digest})"
                        )
        return True

    async def process_saml_response(
        self, tenant_id: str, saml_response_b64: str
    ) -> SamlAssertionPayload:
        config = self._saml_configs.get(tenant_id)
        if not config or not config.enabled:
            raise ValueError(f"SAML IdP is not enabled for tenant '{tenant_id}'")

        try:
            raw_xml = base64.b64decode(saml_response_b64).decode("utf-8")
        except Exception as err:
            raise ValueError(f"Failed to decode base64 SAML response: {err}") from err

        try:
            root = ET.fromstring(raw_xml)
        except Exception as err:
            raise ValueError(f"Invalid SAML XML structure: {err}") from err

        # Cryptographic XMLDSig verification against configured IdP certificate
        if config.idp_x509_cert and config.idp_x509_cert.strip():
            self._verify_saml_signature(root, config.idp_x509_cert)

        # Namespace map for standard SAML 2.0 assertions
        ns = {
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
        }

        # Extract Issuer
        issuer_node = root.find(".//saml:Issuer", ns)
        issuer = issuer_node.text.strip() if issuer_node is not None and issuer_node.text else ""
        if config.idp_entity_id and issuer and issuer != config.idp_entity_id:
            raise ValueError(
                f"SAML Issuer mismatch: expected '{config.idp_entity_id}', got '{issuer}'"
            )

        # Extract Subject NameID (User email)
        name_id_node = root.find(".//saml:Subject/saml:NameID", ns)
        if name_id_node is None or not name_id_node.text:
            raise ValueError("SAML Assertion missing Subject NameID")
        name_id = name_id_node.text.strip()

        # Extract Conditions (Validity window)
        conditions_node = root.find(".//saml:Conditions", ns)
        now_dt = datetime.now(UTC)
        valid_until = now_dt.isoformat()
        if conditions_node is not None:
            not_on_or_after = conditions_node.get("NotOnOrAfter")
            if not_on_or_after:
                valid_until = not_on_or_after
                try:
                    expiry_dt = datetime.fromisoformat(not_on_or_after.replace("Z", "+00:00"))
                    if now_dt > expiry_dt:
                        raise ValueError(f"SAML Assertion expired at {not_on_or_after}")
                except ValueError as ve:
                    if "expired" in str(ve):
                        raise
                    # Ignore date parse quirks in mock assertions
                    pass

        # Extract Attributes
        attributes: dict[str, Any] = {}
        for attr_node in root.findall(".//saml:AttributeStatement/saml:Attribute", ns):
            attr_name = attr_node.get("Name", "")
            values = [v.text.strip() for v in attr_node.findall("saml:AttributeValue", ns) if v.text]
            if values:
                attributes[attr_name] = values if len(values) > 1 else values[0]

        # Extract Security Groups via configured mapping or standard fallback
        group_attr_name = config.attribute_mapping.get("groups", "groups")
        raw_groups = (
            attributes.get(group_attr_name)
            or attributes.get("groups")
            or attributes.get("http://schemas.xmlsoap.org/claims/Group")
            or []
        )
        if isinstance(raw_groups, str):
            groups = [g.strip() for g in raw_groups.split(",") if g.strip()]
        elif isinstance(raw_groups, list):
            groups = [str(g) for g in raw_groups]
        else:
            groups = []

        # Ensure default groups are assigned
        for dg in config.default_groups:
            if dg not in groups:
                groups.append(dg)

        session_index = str(uuid.uuid4())

        return SamlAssertionPayload(
            tenant_id=tenant_id,
            name_id=name_id,
            session_index=session_index,
            attributes=attributes,
            security_groups=groups,
            issuer=issuer or config.idp_entity_id,
            issue_instant=now_dt.isoformat(),
            valid_until=valid_until,
            is_verified=True,
        )

    async def generate_scim_token(self, tenant_id: str) -> str:
        token = f"scim_live_{secrets.token_urlsafe(32)}"
        self._scim_tokens[tenant_id] = token
        return token

    async def list_scim_users(
        self,
        tenant_id: str,
        start_index: int = 1,
        count: int = 20,
        filter_query: str | None = None,
    ) -> ScimListResponse[ScimUser]:
        self._ensure_tenant_storage(tenant_id)
        all_users = list(self._users[tenant_id].values())

        if filter_query:
            # Parse simple RFC 7644 eq filter: e.g. userName eq "user@example.com"
            query_lower = filter_query.lower()
            if " eq " in query_lower:
                parts = filter_query.split(" eq ")
                attr_name = parts[0].strip().lower()
                val = parts[1].strip().strip('"').strip("'").lower()
                if attr_name in ("username", "emails.value"):
                    all_users = [u for u in all_users if u.userName.lower() == val]
                elif attr_name == "active":
                    all_users = [u for u in all_users if str(u.active).lower() == val]

        total = len(all_users)
        start = max(1, start_index) - 1
        page_users = all_users[start : start + count]

        return ScimListResponse[ScimUser](
            totalResults=total,
            startIndex=start_index,
            itemsPerPage=count,
            Resources=page_users,
        )

    async def create_scim_user(self, tenant_id: str, user: dict[str, Any]) -> ScimUser:
        self._ensure_tenant_storage(tenant_id)
        user_id = user.get("id") or f"usr_{uuid.uuid4().hex[:12]}"
        user_name = user.get("userName") or user.get("emails", [{}])[0].get("value", "")
        if not user_name:
            raise ValueError("SCIM User requires 'userName' or valid email")

        now = datetime.now(UTC).isoformat()
        raw_emails = user.get("emails", [{"value": user_name, "primary": True}])
        emails = [
            ScimEmail(
                value=e.get("value", user_name),
                primary=e.get("primary", True),
                type=e.get("type", "work"),
            )
            for e in raw_emails
        ]

        scim_user = ScimUser(
            id=user_id,
            externalId=user.get("externalId"),
            userName=user_name,
            displayName=user.get("displayName") or user_name.split("@")[0],
            active=user.get("active", True),
            emails=emails,
            groups=user.get("groups", []),
            meta=ScimMeta(
                resourceType="User",
                created=now,
                lastModified=now,
                location=f"/v1/scim/v2/tenants/{tenant_id}/Users/{user_id}",
            ),
        )
        self._users[tenant_id][user_id] = scim_user
        return scim_user

    async def get_scim_user(self, tenant_id: str, user_id: str) -> ScimUser | None:
        self._ensure_tenant_storage(tenant_id)
        return self._users[tenant_id].get(user_id)

    async def patch_scim_user(
        self, tenant_id: str, user_id: str, operations: list[dict[str, Any]]
    ) -> ScimUser:
        self._ensure_tenant_storage(tenant_id)
        user = self._users[tenant_id].get(user_id)
        if not user:
            raise KeyError(f"SCIM User '{user_id}' not found")

        now = datetime.now(UTC).isoformat()
        for op in operations:
            op_type = op.get("op", "").lower()
            path = op.get("path", "")
            val = op.get("value")

            if op_type in ("replace", "add"):
                if path == "active" or (isinstance(val, dict) and "active" in val):
                    user.active = bool(val.get("active") if isinstance(val, dict) else val)
                elif path == "displayName":
                    user.displayName = str(val)
                elif path == "userName":
                    user.userName = str(val)

        user.meta.lastModified = now
        self._users[tenant_id][user_id] = user
        return user

    async def delete_scim_user(self, tenant_id: str, user_id: str) -> bool:
        self._ensure_tenant_storage(tenant_id)
        if user_id in self._users[tenant_id]:
            del self._users[tenant_id][user_id]
            return True
        return False

    async def list_scim_groups(
        self, tenant_id: str, start_index: int = 1, count: int = 20
    ) -> ScimListResponse[ScimGroup]:
        self._ensure_tenant_storage(tenant_id)
        all_groups = list(self._groups[tenant_id].values())
        total = len(all_groups)
        start = max(1, start_index) - 1
        page_groups = all_groups[start : start + count]

        return ScimListResponse[ScimGroup](
            totalResults=total,
            startIndex=start_index,
            itemsPerPage=count,
            Resources=page_groups,
        )

    async def create_scim_group(self, tenant_id: str, group: dict[str, Any]) -> ScimGroup:
        self._ensure_tenant_storage(tenant_id)
        group_id = group.get("id") or f"grp_{uuid.uuid4().hex[:10]}"
        display_name = group.get("displayName", "Unnamed Group")
        now = datetime.now(UTC).isoformat()

        raw_members = group.get("members", [])
        members = [
            ScimGroupMember(
                value=m.get("value", ""),
                display=m.get("display"),
                ref=m.get("$ref"),
            )
            for m in raw_members
            if m.get("value")
        ]

        scim_group = ScimGroup(
            id=group_id,
            displayName=display_name,
            members=members,
            meta=ScimMeta(
                resourceType="Group",
                created=now,
                lastModified=now,
                location=f"/v1/scim/v2/tenants/{tenant_id}/Groups/{group_id}",
            ),
        )
        self._groups[tenant_id][group_id] = scim_group
        return scim_group

    async def get_scim_group(self, tenant_id: str, group_id: str) -> ScimGroup | None:
        self._ensure_tenant_storage(tenant_id)
        return self._groups[tenant_id].get(group_id)

    async def patch_scim_group(
        self, tenant_id: str, group_id: str, operations: list[dict[str, Any]]
    ) -> ScimGroup:
        self._ensure_tenant_storage(tenant_id)
        group = self._groups[tenant_id].get(group_id)
        if not group:
            raise KeyError(f"SCIM Group '{group_id}' not found")

        now = datetime.now(UTC).isoformat()
        for op in operations:
            op_type = op.get("op", "").lower()
            val = op.get("value", [])
            if not isinstance(val, list):
                val = [val]

            if op_type == "add":
                existing_values = {m.value for m in group.members}
                for item in val:
                    m_val = item.get("value") if isinstance(item, dict) else str(item)
                    if m_val and m_val not in existing_values:
                        group.members.append(
                            ScimGroupMember(
                                value=m_val,
                                display=item.get("display") if isinstance(item, dict) else None,
                            )
                        )
            elif op_type == "remove":
                remove_values = {
                    (item.get("value") if isinstance(item, dict) else str(item))
                    for item in val
                }
                group.members = [m for m in group.members if m.value not in remove_values]

        group.meta.lastModified = now
        self._groups[tenant_id][group_id] = group
        return group

    async def delete_scim_group(self, tenant_id: str, group_id: str) -> bool:
        self._ensure_tenant_storage(tenant_id)
        if group_id in self._groups[tenant_id]:
            del self._groups[tenant_id][group_id]
            return True
        return False

    async def enforce_rbvac(
        self,
        tenant_id: str,
        user_context: AccessControlContext,
        candidates: list[RbVacCandidateChunk],
    ) -> RbVacSimulationResult:
        start_time = time.perf_counter()
        user_groups_set = {g.strip().lower() for g in user_context.security_groups}

        allowed_chunks: list[RbVacCandidateChunk] = []
        pruned_records: list[RbVacPrunedTelemetry] = []

        for chunk in candidates:
            chunk_acls = [acl.strip().lower() for acl in chunk.acl_groups]

            # Public chunks (explicit '*' or 'public') are universally accessible
            if "*" in chunk_acls or "public" in chunk_acls:
                allowed_chunks.append(chunk)
                continue

            # Role-Based Set Intersection: chunk is accessible if user possesses at least 1 matching group
            matching_groups = user_groups_set.intersection(chunk_acls)
            if matching_groups:
                allowed_chunks.append(chunk)
            else:
                pruned_records.append(
                    RbVacPrunedTelemetry(
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        required_acl_groups=chunk.acl_groups,
                        user_groups=user_context.security_groups,
                        similarity_score=chunk.score,
                        reason=(
                            f"Access denied: Insufficient security group clearance (Required: {chunk.acl_groups}, "
                            f"user holds {user_context.security_groups})"
                        ),
                    )
                )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        return RbVacSimulationResult(
            tenant_id=tenant_id,
            user_id=user_context.user_id,
            user_groups=user_context.security_groups,
            total_candidates=len(candidates),
            allowed_candidates=allowed_chunks,
            pruned_telemetry=pruned_records,
            execution_time_ms=round(duration_ms, 3),
        )
