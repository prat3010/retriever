"""Automated Pytest Suite for Milestone 92: DSPy Declarative Prompt Compilation.

Validates domain models, teleprompter optimization algorithms (BootstrapFewShot, MIPROv2),
PostgreSQL repository isolation, PromptBuilder active injection, and REST APIs.
"""

import ast
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.adapters.cognitive.dspy_compiler_adapter import DSPyCompilerAdapter
from src.adapters.database.compiled_prompt_repository import SqlCompiledPromptRepository
from src.config import settings
from src.domain.abstractions.exceptions import TenantIsolationViolationError
from src.domain.abstractions.inference import PromptTemplate
from src.domain.inference.dspy_abstractions import (
    CompiledPromptProgram,
    FewShotDemonstration,
    PromptCompilationRequest,
)
from src.domain.inference.prompt_builder import PromptBuilder
from src.main import app


class MockTemplateRegistry:
    """Mock PromptTemplateRegistry for PromptBuilder tests."""

    def __init__(self) -> None:
        self.templates = {
            "default": "You are a standard handcrafted default assistant."
        }

    async def get_template(self, tenant_id: str, name: str) -> PromptTemplate | None:
        content = self.templates.get(name, "Default content")
        return PromptTemplate(tenant_id=tenant_id, name=name, content=content)


@pytest.mark.asyncio
async def test_dspy_abstractions_and_models():
    """Verify domain model schemas and serialization."""
    demo = FewShotDemonstration(
        question="What is the refund turnaround?",
        context="Refunds take 7 business days.",
        thought="Extract turnaround time directly.",
        answer="7 business days.",
        score=0.95,
    )
    assert demo.question == "What is the refund turnaround?"
    assert demo.score == 0.95

    program = CompiledPromptProgram(
        program_id="prog_test_123",
        tenant_id=str(uuid.uuid4()),
        name="test_program",
        optimizer="BootstrapFewShot",
        baseline_score=0.65,
        compiled_score=0.88,
        improvement_pct=35.38,
        compiled_instruction="Optimized system instructions.",
        few_shot_demos=[demo],
        is_active=True,
    )
    assert program.program_id == "prog_test_123"
    assert program.is_active is True
    assert len(program.few_shot_demos) == 1


@pytest.mark.asyncio
async def test_dspy_compiler_bootstrap_few_shot():
    """Verify BootstrapFewShot teleprompter optimization against dataset."""
    compiler = DSPyCompilerAdapter(llm_provider=None)

    train_data = [
        {
            "question": "What is the maximum file upload size?",
            "context": "The maximum file upload size is 50MB per document.",
            "ground_truth_answer": "50MB per document.",
        },
        {
            "question": "What encryption standard is used?",
            "context": "All stored chunks use AES-256-GCM envelope encryption.",
            "ground_truth_answer": "AES-256-GCM envelope encryption.",
        },
    ]
    val_data = list(train_data)

    req = PromptCompilationRequest(
        tenant_id=str(uuid.uuid4()),
        optimizer="BootstrapFewShot",
        max_demos=2,
        metric_target="composite",
    )

    result = await compiler.compile_prompt(req, train_data, val_data)

    assert result.program_id.startswith("prog_")
    assert result.baseline_score > 0.0
    assert result.compiled_score > result.baseline_score
    assert result.improvement_pct > 0.0
    assert len(result.few_shot_demos) <= 2
    assert "Retriever's optimized cognitive agent" in result.compiled_instruction


@pytest.mark.asyncio
async def test_dspy_compiler_miprov2():
    """Verify MIPROv2 instruction proposal and optimization."""
    compiler = DSPyCompilerAdapter(llm_provider=None)

    train_data = [
        {
            "question": "Where is customer data hosted?",
            "context": "All European tenant data is strictly hosted in Frankfurt (eu-central-1).",
            "ground_truth_answer": "Frankfurt (eu-central-1).",
        }
    ]

    req = PromptCompilationRequest(
        tenant_id=str(uuid.uuid4()),
        optimizer="MIPROv2",
        max_demos=1,
        metric_target="faithfulness",
    )

    result = await compiler.compile_prompt(req, train_data, train_data)

    assert result.optimizer == "MIPROv2"
    assert result.compiled_score >= result.baseline_score
    assert len(result.few_shot_demos) == 1


@pytest.mark.asyncio
async def test_compiled_prompt_repository_crud_and_isolation():
    """Verify persistent repository operations and tenant boundary enforcement."""
    repo = SqlCompiledPromptRepository()
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    program_a = CompiledPromptProgram(
        program_id="prog_a_01",
        tenant_id=tenant_a,
        name="prog_a",
        baseline_score=0.60,
        compiled_score=0.85,
        compiled_instruction="Instruction for Tenant A",
        is_active=False,
    )

    # Save and retrieve
    await repo.save_program(program_a)
    fetched = await repo.get_program(tenant_a, "prog_a_01")
    assert fetched is not None
    assert fetched.program_id == "prog_a_01"
    assert fetched.compiled_instruction == "Instruction for Tenant A"

    # Cross-tenant isolation check
    fetched_cross = await repo.get_program(tenant_b, "prog_a_01")
    assert fetched_cross is None

    # Invalid UUID must raise TenantIsolationViolationError
    with pytest.raises(TenantIsolationViolationError):
        await repo.get_program("invalid-tenant-id", "prog_a_01")

    # List programs
    listed = await repo.list_programs(tenant_a)
    assert len(listed) >= 1

    # Delete
    deleted = await repo.delete_program(tenant_a, "prog_a_01")
    assert deleted is True
    assert await repo.get_program(tenant_a, "prog_a_01") is None


@pytest.mark.asyncio
async def test_active_program_hot_activation():
    """Verify that activating program 2 atomically deactivates program 1."""
    repo = SqlCompiledPromptRepository()
    tenant_id = str(uuid.uuid4())

    prog1 = CompiledPromptProgram(
        program_id="prog_01",
        tenant_id=tenant_id,
        name="Program 1",
        is_active=False,
    )
    prog2 = CompiledPromptProgram(
        program_id="prog_02",
        tenant_id=tenant_id,
        name="Program 2",
        is_active=False,
    )

    await repo.save_program(prog1)
    await repo.save_program(prog2)

    # Initially no active program
    active = await repo.get_active_program(tenant_id)
    assert active is None

    # Activate Program 1
    activated = await repo.activate_program(tenant_id, "prog_01")
    assert activated is True
    active = await repo.get_active_program(tenant_id)
    assert active is not None
    assert active.program_id == "prog_01"

    # Activate Program 2 -> Program 1 must be deactivated
    activated2 = await repo.activate_program(tenant_id, "prog_02")
    assert activated2 is True
    active2 = await repo.get_active_program(tenant_id)
    assert active2 is not None
    assert active2.program_id == "prog_02"

    prog1_check = await repo.get_program(tenant_id, "prog_01")
    assert prog1_check is not None
    assert prog1_check.is_active is False

    # Deactivate Program 2
    await repo.deactivate_program(tenant_id, "prog_02")
    assert await repo.get_active_program(tenant_id) is None


@pytest.mark.asyncio
async def test_prompt_builder_compiled_injection():
    """Verify PromptBuilder dynamically injects active compiled prompt instructions & demonstrations."""
    template_registry = MockTemplateRegistry()
    repo = SqlCompiledPromptRepository()
    tenant_id = str(uuid.uuid4())

    builder = PromptBuilder(
        template_registry=template_registry,
        compiled_prompt_repo=repo,
    )

    # Case 1: No active compiled prompt -> uses default template
    messages_default = await builder.build_messages(
        tenant_id=tenant_id,
        query="Tell me about pricing",
        history=[],
        context_chunks=[{"chunk_id": "c1", "content": "Basic plan is $10/mo."}],
    )
    assert "You are a standard handcrafted default assistant." in messages_default[0].content
    assert len(messages_default) == 3  # system, context, user

    # Case 2: Active compiled prompt with demonstrations
    compiled_prog = CompiledPromptProgram(
        program_id="prog_active_dsp",
        tenant_id=tenant_id,
        compiled_instruction="DSPy OPTIMIZED SYSTEM PROMPT: Extract strictly grounded facts.",
        few_shot_demos=[
            FewShotDemonstration(
                question="What is the cost?",
                context="Pro plan is $40/mo.",
                thought="Identify monthly fee.",
                answer="The Pro plan costs $40/mo.",
            )
        ],
        is_active=True,
    )
    await repo.save_program(compiled_prog)
    await repo.activate_program(tenant_id, "prog_active_dsp")

    messages_compiled = await builder.build_messages(
        tenant_id=tenant_id,
        query="Tell me about pricing",
        history=[],
        context_chunks=[{"chunk_id": "c1", "content": "Basic plan is $10/mo."}],
    )

    # Primary system message must contain DSPy compiled instruction
    assert "DSPy OPTIMIZED SYSTEM PROMPT" in messages_compiled[0].content
    # Demonstration messages injected before context
    demo_contents = [m.content for m in messages_compiled]
    assert any("What is the cost?" in c for c in demo_contents)
    assert any("The Pro plan costs $40/mo." in c for c in demo_contents)


@pytest.mark.asyncio
async def test_prompts_api_endpoints():
    """Verify FastAPI router endpoints for prompt compilation and lifecycle."""
    tenant_id = str(uuid.uuid4())
    headers = {"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Compile prompt
        compile_payload = {
            "name": "support_cot_optimized",
            "optimizer": "BootstrapFewShot",
            "max_demos": 3,
            "metric_target": "composite",
        }
        res_compile = await client.post(
            f"/v1/tenants/{tenant_id}/prompts/compile",
            json=compile_payload,
            headers=headers,
        )
        assert res_compile.status_code == 200
        compile_data = res_compile.json()
        prog_id = compile_data["program_id"]
        assert prog_id.startswith("prog_")
        assert compile_data["compiled_score"] > 0

        # 2. List compiled prompts
        res_list = await client.get(
            f"/v1/tenants/{tenant_id}/prompts/compiled",
            headers=headers,
        )
        assert res_list.status_code == 200
        programs = res_list.json()
        assert len(programs) >= 1

        # 3. Activate prompt
        res_activate = await client.post(
            f"/v1/tenants/{tenant_id}/prompts/compiled/{prog_id}/activate",
            headers=headers,
        )
        assert res_activate.status_code == 200
        assert res_activate.json()["is_active"] is True

        # 4. Get active prompt
        res_active = await client.get(
            f"/v1/tenants/{tenant_id}/prompts/compiled/active",
            headers=headers,
        )
        assert res_active.status_code == 200
        assert res_active.json()["program_id"] == prog_id

        # 5. Deactivate prompt
        res_deact = await client.post(
            f"/v1/tenants/{tenant_id}/prompts/compiled/{prog_id}/deactivate",
            headers=headers,
        )
        assert res_deact.status_code == 200
        assert res_deact.json()["is_active"] is False

        # 6. Delete prompt
        res_del = await client.delete(
            f"/v1/tenants/{tenant_id}/prompts/compiled/{prog_id}",
            headers=headers,
        )
        assert res_del.status_code == 200
        assert res_del.json()["success"] is True


def test_hexagonal_architecture_boundaries():
    """Verify that domain abstractions contain ZERO framework imports."""
    domain_file = (
        Path(__file__).parent.parent
        / "src"
        / "domain"
        / "inference"
        / "dspy_abstractions.py"
    )
    assert domain_file.exists()

    tree = ast.parse(domain_file.read_text())
    forbidden = {"fastapi", "sqlalchemy", "dspy", "pika", "redis", "httpx"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_pkg = alias.name.split(".")[0]
                assert (
                    root_pkg not in forbidden
                ), f"Domain dspy_abstractions imports forbidden framework: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root_pkg = node.module.split(".")[0]
                assert (
                    root_pkg not in forbidden
                ), f"Domain dspy_abstractions imports forbidden framework: {node.module}"
