"""Cryptographic Compliance & GDPR Deletion Certificate Authority (Milestone 88).

Issues tamper-evident, HMAC-SHA256 signed certificates proving permanent data erasure
for SOC 2, HIPAA, and GDPR Article 17 ("Right to Erasure") regulatory compliance audits.
"""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

from src.domain.abstractions.compliance import (
    ComplianceCertificateDTO,
    ErasureScope,
)


class ComplianceCertificateService:
    """Domain service for generating and cryptographically verifying tamper-evident deletion certificates."""

    def __init__(self, signing_key: str = "dev-retriever-jwt-secret-change-me") -> None:
        self._signing_key = signing_key.encode("utf-8")

    def _canonicalize_records(self, records_purged: dict[str, int]) -> str:
        """Deterministically sort records for canonical signature string construction."""
        sorted_keys = sorted(records_purged.keys())
        return json.dumps({k: records_purged[k] for k in sorted_keys}, separators=(",", ":"))

    def _compute_signature(
        self,
        certificate_id: str,
        tenant_id: str,
        erasure_scope: str,
        target_id: str | None,
        iso_timestamp: str,
        canonical_records: str,
    ) -> str:
        """Compute HMAC-SHA256 digest over the canonical certificate state."""
        canonical_payload = (
            f"{certificate_id}|{tenant_id}|{erasure_scope}|{target_id or 'NONE'}|"
            f"{iso_timestamp}|{canonical_records}"
        )
        return hmac.new(
            self._signing_key,
            canonical_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def issue_certificate(
        self,
        tenant_id: str,
        requester: str,
        reason: str,
        erasure_scope: ErasureScope,
        records_purged: dict[str, int],
        target_id: str | None = None,
    ) -> ComplianceCertificateDTO:
        """Issue an immutable, cryptographically signed compliance deletion certificate."""
        cert_id = f"cert_gdpr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        iso_timestamp = now.isoformat()
        canonical_records = self._canonicalize_records(records_purged)

        sig = self._compute_signature(
            certificate_id=cert_id,
            tenant_id=tenant_id,
            erasure_scope=erasure_scope.value,
            target_id=target_id,
            iso_timestamp=iso_timestamp,
            canonical_records=canonical_records,
        )

        return ComplianceCertificateDTO(
            certificate_id=cert_id,
            tenant_id=tenant_id,
            requester=requester,
            reason=reason,
            timestamp=now,
            erasure_scope=erasure_scope,
            target_id=target_id,
            records_purged=records_purged,
            sha256_audit_signature=sig,
            verification_status="VALID",
        )

    def verify_certificate(self, certificate: ComplianceCertificateDTO) -> bool:
        """Verify the integrity and authenticity of a compliance deletion certificate."""
        iso_timestamp = certificate.timestamp.isoformat()
        canonical_records = self._canonicalize_records(certificate.records_purged)

        expected_sig = self._compute_signature(
            certificate_id=certificate.certificate_id,
            tenant_id=certificate.tenant_id,
            erasure_scope=certificate.erasure_scope.value,
            target_id=certificate.target_id,
            iso_timestamp=iso_timestamp,
            canonical_records=canonical_records,
        )

        return hmac.compare_digest(certificate.sha256_audit_signature, expected_sig)
