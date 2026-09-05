"""Autonomous FDE Metaprogrammer & Self-Extending Capability Studio Abstractions (M97).

Defines pure domain models, manifests, protocols, and abstract interfaces for
dual-persona capability recommendation, static AST boundary checking, code scaffolding,
and dynamic plugin runtime integration. Strictly conforms to Hexagonal boundaries
with zero infrastructure or framework imports.
"""

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SolutionPersona(StrEnum):
    """User persona selecting the appropriate abstraction level."""

    BUSINESS = "business"
    FDE_ENGINEER = "fde_engineer"


class ScaffoldedModuleType(StrEnum):
    """Component module type within a scaffolded Hexagonal architecture slice."""

    ABSTRACTIONS = "abstractions"
    SERVICE = "service"
    ADAPTER = "adapter"
    ROUTER = "router"
    TEST = "test"
    MANIFEST = "manifest"


class PluginCategory(StrEnum):
    """Functional taxonomy of extensible platform plugins."""

    CONNECTORS = "connectors"
    RETRIEVAL = "retrieval"
    AGENTIC_TOOL = "agentic_tool"
    WORKFLOW_STEP = "workflow_step"
    SAFETY_DEFENSE = "safety_defense"
    COMPUTATION = "computation"
    SYSTEM_EXTENSIBILITY = "system_extensibility"


class AgenticToolDeclaration(BaseModel):
    """Declaration of an agent-callable tool provided by this plugin."""

    name: str = Field(..., description="Unique tool identifier for LLM function calling")
    description: str = Field(..., description="Detailed description guiding LLM when to invoke tool")
    method_name: str = Field(default="execute", description="Method name on the domain service")


class IntegrationHooksDeclaration(BaseModel):
    """Declarative runtime integration hooks connecting the plugin to core platform engines."""

    api_router: str | None = Field(
        default=None,
        description="Path to APIRouter variable e.g. 'router.router' to mount under /v1/plugins/{id}",
    )
    battery_service: bool = Field(
        default=True,
        description="Whether to register this plugin into BatteryService catalog as a custom battery",
    )
    agentic_tool: AgenticToolDeclaration | None = Field(
        default=None,
        description="Optional tool configuration registering the plugin into LangGraph agent tool catalog",
    )
    workflow_step: str | None = Field(
        default=None,
        description="Optional step identifier e.g. 'custom.plugin_id.step' for DurableWorkflowEngine",
    )


class PluginManifest(BaseModel):
    """Strict contract manifest defining metadata, dependencies, and hooks for a plugin."""

    id: str = Field(..., description="Unique snake_case slug identifier e.g. 'hubspot_crm_sync'")
    name: str = Field(..., description="Human-readable display name")
    version: str = Field(default="1.0.0", description="Semver release version")
    category: PluginCategory = Field(default=PluginCategory.SYSTEM_EXTENSIBILITY)
    persona: SolutionPersona = Field(default=SolutionPersona.FDE_ENGINEER)
    description: str = Field(..., description="Comprehensive functional description")
    algorithm_foundation: str = Field(
        default="Hexagonal Domain Service with Dependency Injection",
        description="Algorithmic or mathematical foundation",
    )
    latency_profile: str = Field(default="~20ms", description="Benchmark latency estimate")
    integration_hooks: IntegrationHooksDeclaration = Field(
        default_factory=IntegrationHooksDeclaration,
        description="Runtime hooks into core platform systems",
    )
    required_secrets: list[str] = Field(
        default_factory=list,
        description="Environment variable names required at runtime (e.g. ['HUBSPOT_API_KEY'])",
    )
    tenant_isolation: str = Field(
        default="tenant_scoped",
        description="'tenant_scoped' or 'global_system'",
    )


class UseCaseRequirement(BaseModel):
    """Input specification describing a business problem or technical integration requirement."""

    prompt: str = Field(..., description="Natural language description of problem or integration")
    target_domain: str = Field(
        default="general",
        description="Domain context e.g. 'healthcare', 'fintech', 'crm', 'ecommerce'",
    )
    tenant_id: str = Field(default="system", description="Tenant requesting or owning this capability")
    persona: SolutionPersona = Field(
        default=SolutionPersona.BUSINESS,
        description="Target user persona (business wizard vs FDE code generator)",
    )
    preferred_stack: str | None = Field(
        default="fastapi_python",
        description="Target implementation stack",
    )


class RecommendedBatteryConfig(BaseModel):
    """Recommended existing platform battery matching a requirement."""

    battery_id: str
    battery_name: str
    category: str
    match_confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str
    suggested_hyperparameters: dict[str, Any] = Field(default_factory=dict)
    health_check_endpoint: str | None = None


class ScaffoldedFile(BaseModel):
    """A single generated source code or configuration file."""

    rel_path: str = Field(..., description="Relative file path within plugin package")
    content: str = Field(..., description="Full source code text")
    module_type: ScaffoldedModuleType


class AstValidationResult(BaseModel):
    """Result of static AST parsing and boundary analysis."""

    is_valid: bool = True
    violations: list[str] = Field(default_factory=list)
    forbidden_imports_found: list[str] = Field(default_factory=list)
    type_annotations_present: bool = True
    syntax_valid: bool = True
    summary: str = "AST conformance passed with 0 architectural violations."


class ScaffoldingPlan(BaseModel):
    """Complete scaffolding plan containing matched batteries and generated code slices."""

    plugin_id: str
    display_name: str
    description: str
    persona: SolutionPersona
    manifest: PluginManifest
    recommended_batteries: list[RecommendedBatteryConfig] = Field(default_factory=list)
    needs_custom_scaffold: bool = False
    scaffolded_files: list[ScaffoldedFile] = Field(default_factory=list)
    ast_audit_passed: bool = True
    ast_validation: AstValidationResult | None = None
    git_branch_name: str = ""
    pull_request_markdown: str = ""


class CustomPluginSummary(BaseModel):
    """Summary of an installed custom plugin in the system."""

    plugin_id: str
    display_name: str
    version: str
    category: str
    persona: str
    description: str
    is_active: bool = True
    hooks: IntegrationHooksDeclaration = Field(default_factory=IntegrationHooksDeclaration)
    created_at: str | None = None
    updated_at: str | None = None


# ── Abstract Domain Protocols (Hexagonal Ports) ─────────────────────────────


class RequirementAnalyzerProtocol(ABC):
    """Port for analyzing natural language requirements against platform capabilities."""

    @abstractmethod
    def analyze(self, req: UseCaseRequirement) -> list[RecommendedBatteryConfig]:
        """Match requirement against platform batteries and return recommendations."""
        ...

    @abstractmethod
    def assess_capability_gap(self, req: UseCaseRequirement) -> bool:
        """Return True if requirement requires custom scaffolding beyond existing batteries."""
        ...


class AstBoundaryValidatorProtocol(ABC):
    """Port for parsing Python code via AST and asserting Hexagonal boundaries."""

    @abstractmethod
    def validate_code(self, code: str, filename: str, is_domain: bool = True) -> AstValidationResult:
        """Inspect source code string and assert Hexagonal rules."""
        ...

    @abstractmethod
    def validate_plugin_files(self, files: list[ScaffoldedFile]) -> AstValidationResult:
        """Validate an entire collection of scaffolded plugin files."""
        ...


class MetaprogrammerProtocol(ABC):
    """Port for synthesizing production-grade Hexagonal code slices."""

    @abstractmethod
    def generate_plan(self, req: UseCaseRequirement) -> ScaffoldingPlan:
        """Generate complete scaffolding plan with AST-verified code slices."""
        ...


class PluginManagerProtocol(ABC):
    """Port for discovering, validating, loading, and mounting custom plugins."""

    @abstractmethod
    def discover_plugins(self) -> list[CustomPluginSummary]:
        """Scan custom plugins directory and return discovered plugin summaries."""
        ...

    @abstractmethod
    def get_plugin_manifest(self, plugin_id: str) -> PluginManifest | None:
        """Read and validate manifest for a specific plugin."""
        ...
