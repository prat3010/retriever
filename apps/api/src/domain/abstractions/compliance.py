from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PiiCategory(StrEnum):
    FINANCIAL = "financial"  # Credit Cards (Luhn validated), IBAN, Bank Accounts
    IDENTIFICATION = "identification"  # SSN, Passports, Aadhaar, PAN, Driver's License
    SECRETS = "secrets"  # AWS keys, OpenAI keys, GitHub tokens, JWTs, Private Keys
    NETWORK = "network"  # IPv4, IPv6, MAC Addresses
    HEALTH_HIPAA = "health_hipaa"  # Medical Record Numbers, Health Insurance Policy IDs
    CONTACT = "contact"  # Email, Phone numbers
    CUSTOM = "custom"  # Custom user-defined regex patterns


class MaskingMode(StrEnum):
    REDACT = "redact"  # [REDACTED_FINANCIAL]
    SYNTHETIC = "synthetic"  # e.g. **** **** **** 1234 or ***-**-1234
    PSEUDONYMIZE = "pseudonymize"  # [PSEUDONYM:a1b2c3d4]


class PiiEntityMatch(BaseModel):
    category: PiiCategory
    entity_type: str
    original_value: str
    masked_value: str
    start: int
    end: int


class PiiRedactionRequest(BaseModel):
    text: str
    categories: list[PiiCategory] | None = None
    masking_mode: MaskingMode = MaskingMode.REDACT
    custom_patterns: list[str] | None = None


class PiiRedactionResponse(BaseModel):
    original_length: int
    redacted_text: str
    entities_detected: list[PiiEntityMatch]
    total_redacted: int


class ErasureScope(StrEnum):
    DOCUMENT = "document"
    FULL_TENANT_WIPE = "full_tenant_wipe"


class ComplianceCertificateDTO(BaseModel):
    certificate_id: str = Field(..., description="Unique compliance deletion certificate identifier, e.g. 'cert_gdpr_...'")
    tenant_id: str
    requester: str
    reason: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    erasure_scope: ErasureScope
    target_id: str | None = None
    records_purged: dict[str, int]
    sha256_audit_signature: str
    verification_status: str = "VALID"


class CompliancePurgeRequest(BaseModel):
    requester: str
    reason: str = "GDPR Article 17 Right to Erasure Request"
    document_id: str | None = None  # None indicates full tenant purge


class ComplianceVerificationResponse(BaseModel):
    certificate_id: str
    is_valid: bool
    audit_signature: str
    certificate: ComplianceCertificateDTO | None = None
    message: str
