from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SamlIdpConfig(BaseModel):
    """Configuration for a tenant's SAML 2.0 Identity Provider (IdP)."""

    tenant_id: str
    idp_entity_id: str
    sso_url: str
    idp_x509_cert: str
    sp_entity_id: str = "https://rag.prateeq.in/saml"
    acs_url: str = "https://rag.prateeq.in/v1/identity/saml/acs"
    attribute_mapping: dict[str, str] = Field(
        default_factory=lambda: {
            "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "firstName": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
            "lastName": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
            "groups": "http://schemas.xmlsoap.org/claims/Group",
        }
    )
    default_groups: list[str] = Field(default_factory=lambda: ["general"])
    enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class SamlAssertionPayload(BaseModel):
    """Parsed and cryptographically verified SAML 2.0 assertion."""

    tenant_id: str
    name_id: str
    session_index: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    security_groups: list[str] = Field(default_factory=list)
    issuer: str
    issue_instant: str
    valid_until: str
    is_verified: bool = True


class ScimMeta(BaseModel):
    """RFC 7643 SCIM resource metadata."""

    resourceType: str
    created: str
    lastModified: str
    location: str = ""
    version: str = "W/\"1\""


class ScimEmail(BaseModel):
    """RFC 7643 SCIM email entry."""

    value: str
    primary: bool = True
    type: str = "work"


class ScimUser(BaseModel):
    """RFC 7643 SCIM User representation."""

    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"]
    )
    id: str
    externalId: str | None = None
    userName: str
    displayName: str | None = None
    active: bool = True
    emails: list[ScimEmail] = Field(default_factory=list)
    groups: list[dict[str, str]] = Field(default_factory=list)
    meta: ScimMeta


class ScimGroupMember(BaseModel):
    """RFC 7643 SCIM Group member entry."""

    value: str
    display: str | None = None
    ref: str | None = None


class ScimGroup(BaseModel):
    """RFC 7643 SCIM Group representation."""

    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    )
    id: str
    displayName: str
    members: list[ScimGroupMember] = Field(default_factory=list)
    meta: ScimMeta


class ScimListResponse(BaseModel, Generic[T]):
    """RFC 7644 SCIM ListResponse container."""

    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    )
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int = 20
    Resources: list[T] = Field(default_factory=list)


class AccessControlContext(BaseModel):
    """Security clearance context of an authenticated user."""

    user_id: str
    tenant_id: str
    email: str
    security_groups: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)


class RbVacFilter(BaseModel):
    """Constraints for Role-Based Vector Access Control filtering."""

    user_groups: list[str] = Field(default_factory=list)
    allow_public: bool = True
    strict_mode: bool = True


class RbVacPrunedTelemetry(BaseModel):
    """Audit record of a retrieval candidate pruned by RB-VAC."""

    chunk_id: str
    document_id: str
    required_acl_groups: list[str]
    user_groups: list[str]
    similarity_score: float
    reason: str = "Insufficient security group clearance"


class RbVacCandidateChunk(BaseModel):
    """Candidate chunk evaluated by RB-VAC."""

    chunk_id: str
    document_id: str
    content: str
    score: float
    acl_groups: list[str] = Field(default_factory=lambda: ["*"])
    classification: str = "internal"


class RbVacSimulationResult(BaseModel):
    """Result of an RB-VAC simulation or enforcement execution."""

    tenant_id: str
    user_id: str
    user_groups: list[str]
    total_candidates: int
    allowed_candidates: list[RbVacCandidateChunk] = Field(default_factory=list)
    pruned_telemetry: list[RbVacPrunedTelemetry] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class IdentityFederationPort(ABC):
    """Abstract port for SAML 2.0, SCIM 2.0 directory sync, and RB-VAC."""

    @abstractmethod
    async def configure_saml_idp(self, config: SamlIdpConfig) -> SamlIdpConfig:
        """Save or update tenant SAML IdP configuration."""
        pass

    @abstractmethod
    async def get_saml_idp_config(self, tenant_id: str) -> SamlIdpConfig | None:
        """Get tenant SAML IdP configuration."""
        pass

    @abstractmethod
    async def generate_sp_metadata(self, tenant_id: str) -> str:
        """Generate SAML 2.0 Service Provider (SP) metadata XML."""
        pass

    @abstractmethod
    async def process_saml_response(
        self, tenant_id: str, saml_response_b64: str
    ) -> SamlAssertionPayload:
        """Verify XML signature, validate timestamps/audience, and extract attributes."""
        pass

    @abstractmethod
    async def generate_scim_token(self, tenant_id: str) -> str:
        """Generate or rotate SCIM 2.0 bearer authorization token."""
        pass

    @abstractmethod
    async def list_scim_users(
        self, tenant_id: str, start_index: int = 1, count: int = 20, filter_query: str | None = None
    ) -> ScimListResponse[ScimUser]:
        """List SCIM users with pagination and optional query filtering."""
        pass

    @abstractmethod
    async def create_scim_user(self, tenant_id: str, user: dict[str, Any]) -> ScimUser:
        """Provision a new user via SCIM 2.0."""
        pass

    @abstractmethod
    async def get_scim_user(self, tenant_id: str, user_id: str) -> ScimUser | None:
        """Get a SCIM user by ID."""
        pass

    @abstractmethod
    async def patch_scim_user(
        self, tenant_id: str, user_id: str, operations: list[dict[str, Any]]
    ) -> ScimUser:
        """Apply RFC 7644 PATCH operations to user (e.g. active=false)."""
        pass

    @abstractmethod
    async def delete_scim_user(self, tenant_id: str, user_id: str) -> bool:
        """Deprovision a user via SCIM 2.0."""
        pass

    @abstractmethod
    async def list_scim_groups(
        self, tenant_id: str, start_index: int = 1, count: int = 20
    ) -> ScimListResponse[ScimGroup]:
        """List SCIM groups with member counts."""
        pass

    @abstractmethod
    async def create_scim_group(self, tenant_id: str, group: dict[str, Any]) -> ScimGroup:
        """Create a new SCIM group."""
        pass

    @abstractmethod
    async def get_scim_group(self, tenant_id: str, group_id: str) -> ScimGroup | None:
        """Get a SCIM group by ID."""
        pass

    @abstractmethod
    async def patch_scim_group(
        self, tenant_id: str, group_id: str, operations: list[dict[str, Any]]
    ) -> ScimGroup:
        """Update members of a SCIM group."""
        pass

    @abstractmethod
    async def delete_scim_group(self, tenant_id: str, group_id: str) -> bool:
        """Delete a SCIM group."""
        pass

    @abstractmethod
    async def enforce_rbvac(
        self,
        tenant_id: str,
        user_context: AccessControlContext,
        candidates: list[RbVacCandidateChunk],
    ) -> RbVacSimulationResult:
        """Filter vector retrieval candidates against user's security groups."""
        pass
