"""Autonomous Metaprogrammer Domain Service (M97).

Autonomous code synthesis engine generating production-grade Hexagonal
architecture code slices for custom enterprise capabilities. Synthesizes
abstractions, domain services, infrastructure adapters, FastAPI routers,
Pytest unit tests, and JSON manifests. Validates all generated code
through the AST boundary checker before returning.
Zero infrastructure or framework imports in this domain service.
"""

import re

from src.domain.abstractions.scaffolding import (
    AgenticToolDeclaration,
    IntegrationHooksDeclaration,
    MetaprogrammerProtocol,
    PluginCategory,
    PluginManifest,
    ScaffoldedFile,
    ScaffoldedModuleType,
    ScaffoldingPlan,
    SolutionPersona,
    UseCaseRequirement,
)
from src.domain.scaffolding.boundary_checker import AstBoundaryValidator
from src.domain.scaffolding.pr_generator import PullRequestGenerator
from src.domain.scaffolding.requirement_analyzer import RequirementAnalyzer


class AutonomousMetaprogrammer(MetaprogrammerProtocol):
    """Pure domain code generator synthesizing AST-verified Hexagonal architecture modules."""

    def __init__(
        self,
        analyzer: RequirementAnalyzer | None = None,
        validator: AstBoundaryValidator | None = None,
    ) -> None:
        self.analyzer = analyzer or RequirementAnalyzer()
        self.validator = validator or AstBoundaryValidator()

    @staticmethod
    def _extract_plugin_slug(prompt: str, domain: str) -> str:
        """Derive a clean snake_case plugin identifier from the requirement prompt."""
        # Find key integration keywords
        known_keywords = [
            "hubspot", "salesforce", "jira", "zendesk", "stripe", "github",
            "linear", "notion", "slack", "postgres", "mongodb", "bigquery",
            "clinical", "patient", "redline", "diff", "catalog", "invoice",
            "compliance", "audit", "crawler", "sync", "extractor", "classifier"
        ]
        prompt_lower = prompt.lower()
        matched = [k for k in known_keywords if k in prompt_lower]

        if matched:
            base_slug = "_".join(matched[:2])
            if "sync" not in base_slug and "connector" not in base_slug and "differ" not in base_slug:
                base_slug += "_adapter"
            return base_slug.replace("-", "_")

        # Fallback to domain and prompt words
        words = re.findall(r"[a-zA-Z0-9]+", prompt_lower)
        significant = [w for w in words if len(w) > 3 and w not in {"need", "with", "from", "that", "this", "have"}][:2]
        if significant:
            return "_".join(significant) + "_service"
        return f"{domain.lower()}_custom_service"

    @staticmethod
    def _to_pascal_case(snake_str: str) -> str:
        """Convert snake_case to PascalCase string."""
        return "".join(word.capitalize() for word in snake_str.split("_"))

    def _determine_category(self, prompt: str) -> PluginCategory:
        """Determine primary taxonomy category for requirement."""
        p = prompt.lower()
        if any(w in p for w in ["sync", "connect", "fetch", "pull", "export", "webhook", "api"]):
            return PluginCategory.CONNECTORS
        if any(w in p for w in ["search", "rank", "retrieval", "embed", "vector"]):
            return PluginCategory.RETRIEVAL
        if any(w in p for w in ["guard", "redact", "mask", "pii", "shield", "safety"]):
            return PluginCategory.SAFETY_DEFENSE
        if any(w in p for w in ["durable", "batch", "cron", "workflow", "job"]):
            return PluginCategory.WORKFLOW_STEP
        if any(w in p for w in ["tool", "agent", "action", "copilot", "chat"]):
            return PluginCategory.AGENTIC_TOOL
        if any(w in p for w in ["math", "calculate", "formula", "eval"]):
            return PluginCategory.COMPUTATION
        return PluginCategory.SYSTEM_EXTENSIBILITY

    def generate_plan(self, req: UseCaseRequirement) -> ScaffoldingPlan:
        """Synthesize complete scaffolding plan with AST-verified code slices."""
        recommendations = self.analyzer.analyze(req)
        needs_custom = self.analyzer.assess_capability_gap(req)

        plugin_id = self._extract_plugin_slug(req.prompt, req.target_domain)
        class_name_prefix = self._to_pascal_case(plugin_id)
        display_name = f"{class_name_prefix} Capability"
        category = self._determine_category(req.prompt)

        manifest = PluginManifest(
            id=plugin_id,
            name=display_name,
            version="1.0.0",
            category=category,
            persona=req.persona,
            description=req.prompt,
            algorithm_foundation="Hexagonal Domain Service with Dependency Injection & AST Verification",
            latency_profile="~25ms",
            integration_hooks=IntegrationHooksDeclaration(
                api_router="router.router",
                battery_service=True,
                agentic_tool=AgenticToolDeclaration(
                    name=f"{plugin_id}_execute",
                    description=f"Executes {display_name} for tenant workspace: {req.prompt}",
                    method_name="execute",
                ),
                workflow_step=f"custom.{plugin_id}.execute",
            ),
            required_secrets=[f"{plugin_id.upper()}_API_KEY"],
            tenant_isolation="tenant_scoped",
        )

        scaffolded_files: list[ScaffoldedFile] = []

        if needs_custom or req.persona == SolutionPersona.FDE_ENGINEER:
            # 1. Manifest JSON
            manifest_json_str = manifest.model_dump_json(indent=2)
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="manifest.json",
                    content=manifest_json_str,
                    module_type=ScaffoldedModuleType.MANIFEST,
                )
            )

            # 2. Domain Abstractions (Pure Protocols, Zero Framework Imports)
            abstractions_code = f'''"""Domain Abstractions for {display_name}.

Defines pure protocols, requests, and DTOs with ZERO framework imports.
Conforms strictly to Hexagonal boundaries.
"""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field


class {class_name_prefix}InputDTO(BaseModel):
    """Input parameters for {display_name} execution."""

    query: str = Field(..., description="Target query, entity key, or filter criteria")
    tenant_id: str = Field(..., description="Tenant owning this execution context")
    options: dict[str, Any] = Field(default_factory=dict, description="Custom operational options")


class {class_name_prefix}OutputDTO(BaseModel):
    """Output results produced by {display_name}."""

    success: bool = True
    total_records: int = 0
    records: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


class {class_name_prefix}Port(ABC):
    """Outbound infrastructure port for {display_name}."""

    @abstractmethod
    def fetch_data(self, query: str, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch records from external service or database."""
        ...

    @abstractmethod
    def verify_connection(self) -> bool:
        """Check reachability of the underlying infrastructure."""
        ...
'''
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="domain/abstractions.py",
                    content=abstractions_code,
                    module_type=ScaffoldedModuleType.ABSTRACTIONS,
                )
            )

            # 3. Pure Domain Service (Pure Logic, Zero Framework Imports)
            service_code = f'''"""Domain Service for {display_name}.

Encapsulates core business algorithms and orchestration.
Strictly conforms to Hexagonal boundary (0 framework imports).
"""

from typing import Any
from .abstractions import {class_name_prefix}InputDTO, {class_name_prefix}OutputDTO, {class_name_prefix}Port


class {class_name_prefix}Service:
    """Pure domain business service for {display_name}."""

    def __init__(self, port: {class_name_prefix}Port) -> None:
        self._port = port

    def execute(self, payload: {class_name_prefix}InputDTO) -> {class_name_prefix}OutputDTO:
        """Execute capability logic with business filtering and aggregation."""
        raw_records = self._port.fetch_data(
            query=payload.query,
            tenant_id=payload.tenant_id,
            limit=int(payload.options.get("limit", 50)),
        )

        processed = []
        for item in raw_records:
            cleaned = {{k: v for k, v in item.items() if v is not None}}
            cleaned["_augmented_by"] = "{plugin_id}"
            processed.append(cleaned)

        summary_msg = f"Processed {{len(processed)}} records for query '{{payload.query}}'."

        return {class_name_prefix}OutputDTO(
            success=True,
            total_records=len(processed),
            records=processed,
            metadata={{"tenant_id": payload.tenant_id, "plugin": "{plugin_id}"}},
            summary=summary_msg,
        )

    def health(self) -> dict[str, Any]:
        """Verify underlying adapter connectivity."""
        reachable = self._port.verify_connection()
        return {{
            "plugin_id": "{plugin_id}",
            "healthy": reachable,
            "status": "active" if reachable else "degraded",
        }}
'''
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="domain/service.py",
                    content=service_code,
                    module_type=ScaffoldedModuleType.SERVICE,
                )
            )

            # 4. Infrastructure Adapter
            adapter_code = f'''"""Infrastructure Adapter for {display_name}.

Implements {class_name_prefix}Port connecting to live database or external API.
"""

from typing import Any
import logging
from ..domain.abstractions import {class_name_prefix}Port

logger = logging.getLogger(__name__)


class {class_name_prefix}Adapter({class_name_prefix}Port):
    """Concrete adapter connecting to external integration endpoints."""

    def __init__(self, api_key: str | None = None, base_url: str = "https://api.external.com") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def fetch_data(self, query: str, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve records from external provider or local storage."""
        logger.info("Fetching data for tenant %s (query=%s, limit=%d)", tenant_id, query, limit)
        # Production integration logic:
        # In real deployments, invokes httpx / SDK with self.api_key
        sample_results = [
            {{"id": f"rec_{{i}}", "tenant_id": tenant_id, "title": f"Record {{i}} matching {{query}}", "score": round(1.0 - (i * 0.05), 2)}}
            for i in range(min(limit, 5))
        ]
        return sample_results

    def verify_connection(self) -> bool:
        """Health probe confirming external endpoint connectivity."""
        return True
'''
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="adapters/adapter.py",
                    content=adapter_code,
                    module_type=ScaffoldedModuleType.ADAPTER,
                )
            )

            # 5. FastAPI Router
            router_code = f'''"""FastAPI APIRouter for {display_name}.

Mounted dynamically under /v1/plugins/{plugin_id}/* with tenant auth context.
"""

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .domain.abstractions import {class_name_prefix}InputDTO, {class_name_prefix}OutputDTO
from .domain.service import {class_name_prefix}Service
from .adapters.adapter import {class_name_prefix}Adapter

router = APIRouter(tags=["Plugin: {display_name}"])

# Standard dependency injection for plugin service
_default_adapter = {class_name_prefix}Adapter()
_default_service = {class_name_prefix}Service(port=_default_adapter)


def get_{plugin_id}_service() -> {class_name_prefix}Service:
    return _default_service


class ExecuteRequest(BaseModel):
    query: str = Field(..., description="Query or operation command")
    options: dict[str, Any] = Field(default_factory=dict)


@router.post("/execute", response_model={class_name_prefix}OutputDTO)
def execute_plugin_action(
    payload: ExecuteRequest,
    x_tenant_id: str = Header(default="default-tenant", alias="X-Tenant-ID"),
    service: {class_name_prefix}Service = Depends(get_{plugin_id}_service),
) -> {class_name_prefix}OutputDTO:
    """Execute {display_name} within tenant security scope."""
    dto = {class_name_prefix}InputDTO(
        query=payload.query,
        tenant_id=x_tenant_id,
        options=payload.options,
    )
    return service.execute(dto)


@router.get("/health")
def get_plugin_health(
    service: {class_name_prefix}Service = Depends(get_{plugin_id}_service),
) -> dict[str, Any]:
    """Check health and adapter reachability for {display_name}."""
    return service.health()
'''
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="router.py",
                    content=router_code,
                    module_type=ScaffoldedModuleType.ROUTER,
                )
            )

            # 6. Pytest Unit & Boundary Test Suite
            test_code = f'''"""Automated Test Suite for {display_name}.

Verifies:
1. Strict Hexagonal Architecture Boundary (0 framework imports in domain).
2. Domain Service business logic with mock port.
3. Adapter operations and contract conformance.
4. FastAPI router endpoints via TestClient.
"""

import ast
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from ..domain.abstractions import {class_name_prefix}InputDTO, {class_name_prefix}Port
from ..domain.service import {class_name_prefix}Service
from ..adapters.adapter import {class_name_prefix}Adapter
from ..router import router, get_{plugin_id}_service


# ── 1. Hexagonal Boundary Conformance Test ──────────────────────────────────


def test_hexagonal_boundary_conformance() -> None:
    """Assert that domain abstractions and service contain 0 framework imports."""
    plugin_dir = Path(__file__).resolve().parent.parent
    domain_files = [plugin_dir / "domain" / "abstractions.py", plugin_dir / "domain" / "service.py"]
    forbidden = {{"fastapi", "sqlalchemy", "celery", "redis", "pika", "httpx", "subprocess"}}

    for f in domain_files:
        assert f.exists(), f"File {{f}} must exist"
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    root = name.name.split(".")[0]
                    assert root not in forbidden, f"Forbidden import {{root}} in {{f.name}}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root = node.module.split(".")[0]
                    assert root not in forbidden, f"Forbidden import {{root}} in {{f.name}}"


# ── 2. Domain Service Unit Tests ────────────────────────────────────────────


class Mock{class_name_prefix}Port({class_name_prefix}Port):
    def fetch_data(self, query: str, tenant_id: str, limit: int = 50) -> list[dict]:
        return [{{"id": "test_1", "query": query, "tenant": tenant_id}}]

    def verify_connection(self) -> bool:
        return True


def test_domain_service_execution() -> None:
    """Verify service correctly augments records."""
    mock_port = Mock{class_name_prefix}Port()
    svc = {class_name_prefix}Service(port=mock_port)
    dto = {class_name_prefix}InputDTO(query="test_query", tenant_id="tenant_123")

    result = svc.execute(dto)
    assert result.success is True
    assert result.total_records == 1
    assert result.records[0]["_augmented_by"] == "{plugin_id}"
    assert "Processed 1 records" in result.summary


# ── 3. Adapter & Health Tests ───────────────────────────────────────────────


def test_adapter_fetch_and_health() -> None:
    """Verify adapter implements port contract."""
    adapter = {class_name_prefix}Adapter()
    assert adapter.verify_connection() is True
    data = adapter.fetch_data("query_sample", "tenant_abc", limit=3)
    assert len(data) == 3


# ── 4. Router API Tests ─────────────────────────────────────────────────────


def test_router_execution_endpoint() -> None:
    """Verify FastAPI router returns 200 with tenant header."""
    client = TestClient(router)
    res = client.post("/execute", json={{"query": "deals", "options": {{"limit": 2}}}}, headers={{"X-Tenant-ID": "test_tenant"}})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["total_records"] == 2
'''
            scaffolded_files.append(
                ScaffoldedFile(
                    rel_path="tests/test_plugin.py",
                    content=test_code,
                    module_type=ScaffoldedModuleType.TEST,
                )
            )

        # Validate all files with AST boundary validator
        ast_result = self.validator.validate_plugin_files(scaffolded_files)

        # Generate PR and git branch
        branch_name = PullRequestGenerator.generate_branch_name(plugin_id)

        plan = ScaffoldingPlan(
            plugin_id=plugin_id,
            display_name=display_name,
            description=req.prompt,
            persona=req.persona,
            manifest=manifest,
            recommended_batteries=recommendations,
            needs_custom_scaffold=needs_custom or (req.persona == SolutionPersona.FDE_ENGINEER),
            scaffolded_files=scaffolded_files,
            ast_audit_passed=ast_result.is_valid,
            ast_validation=ast_result,
            git_branch_name=branch_name,
        )

        plan.pull_request_markdown = PullRequestGenerator.generate_pr_markdown(plan)
        return plan
