#!/usr/bin/env python3
"""
Seed Demo Tenant & Sample Knowledge Base for Retriever.
Provisions deterministic demo workspace and 'ret_live_demo_...' API key for 30-second onboarding.
"""

import asyncio
import hashlib
import logging
import os
import sys
import uuid
from pathlib import Path

# Add apps/api to sys.path
api_root = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(api_root))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo")

DEMO_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_API_KEY = "ret_live_demo_00000000000000000000000000000000"
DEMO_KEY_HASH = hashlib.sha256(DEMO_API_KEY.encode("utf-8")).hexdigest()
DEMO_KEY_PREFIX = "ret_live_demo"

SAMPLE_CHUNKS = [
    {
        "title": "ColBERT Late Interaction Reranking",
        "content": (
            "ColBERT late interaction computes token-level similarity between query and document "
            "representations using the MaxSim operator. Rather than compressing an entire document "
            "into a single pooled vector, ColBERT retains per-token embeddings. During search, "
            "every query token cross-attends against all document tokens in sub-10ms, capturing "
            "fine-grained technical terms and code symbols that cosine similarity misses."
        ),
        "tags": ["search", "colbert", "reranking"],
    },
    {
        "title": "Hybrid Search Fusion Architecture",
        "content": (
            "Retriever combines pgvector HNSW dense cosine search with PostgreSQL native BM25 lexical search "
            "via Reciprocal Rank Fusion (RRF). Dense search captures semantic conceptual intent, while "
            "BM25 captures exact identifiers, serial numbers, and variable names. An adaptive alpha parameter "
            "(default 0.7) dynamically balances dense versus sparse weighting depending on query complexity."
        ),
        "tags": ["search", "hybrid", "bm25", "pgvector"],
    },
    {
        "title": "Scale-to-Zero Dedicated GPU Serving",
        "content": (
            "Using vLLM 0.6+ and serverless execution via Modal and BentoML, dedicated tenant models scale "
            "down to zero instances after 300 seconds of idle traffic. This eliminates $720/month per tenant "
            "dedicated GPU hosting waste, reducing idle costs to ~$15/month (a 97.9% cost reduction). "
            "Dynamic LoRA tensor swapping enables a single shared base model to execute distinct tenant weights "
            "in ~20ms without container restarts."
        ),
        "tags": ["serving", "vllm", "gpu", "lora"],
    },
    {
        "title": "Cognitive Agent Memory & Long-Horizon Distillation",
        "content": (
            "Retriever's cognitive memory engine incorporates mathematical Ebbinghaus decay: "
            "R(t) = exp(-delta_t / (S * 86400)). On successful downstream task priming, memory stability S "
            "expands as S <- 1.5 * S + 0.5. Offline consolidation daemons synthesize multi-turn ReAct traces "
            "into distilled episodic and procedural guidance notes, priming future agent loops and eliminating "
            "redundant exploratory tool calls."
        ),
        "tags": ["agent", "memory", "ebbinghaus", "react"],
    },
    {
        "title": "Multi-Agent Swarm Quorum Consensus",
        "content": (
            "The multi-agent swarm quorum engine coordinates specialized agent personas (Planner, Auditor, "
            "Synthesizer, and Skeptic) across a dialectic debate DAG. Intermediate tool observations are "
            "cross-examined in multi-round debate. A role-calibrated weighted quorum vote V(A_k) synthesizes "
            "consensus answers, automatically pruning unverified hallucinations before client emission."
        ),
        "tags": ["agent", "swarm", "quorum", "consensus"],
    },
]


async def generate_embedding(text: str, ollama_url: str) -> list[float]:
    """Attempts to generate real embeddings via local Ollama, or falls back to synthetic normalized vector."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
            )
            if resp.status_code == 200:
                data = resp.json()
                if "embedding" in data:
                    return data["embedding"]
    except Exception:
        pass

    # Deterministic fallback vector (768-dim normalized)
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16)
    import random
    rng = random.Random(seed)
    raw = [rng.uniform(-1.0, 1.0) for _ in range(768)]
    norm = sum(x * x for x in raw) ** 0.5 or 1.0
    return [x / norm for x in raw]


async def seed_database():
    from sqlalchemy import select
    from src.adapters.database.connection import async_session_maker
    from src.adapters.database.models import (
        ApiKeyDb,
        DocumentChunkDb,
        DocumentDb,
        TenantConfigDb,
        TenantDb,
    )

    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    async with async_session_maker() as session:
        # 1. Tenant Check / Creation
        stmt = select(TenantDb).where(TenantDb.tenant_id == DEMO_TENANT_ID)
        result = await session.execute(stmt)
        tenant = result.scalar_one_or_none()

        if not tenant:
            logger.info("Creating demo tenant: %s (%s)", DEMO_TENANT_ID, "Demo Enterprise Workspace")
            tenant = TenantDb(
                tenant_id=DEMO_TENANT_ID,
                name="Demo Enterprise Workspace",
                status="active",
                tier="enterprise",
            )
            session.add(tenant)
            await session.flush()
        else:
            logger.info("Demo tenant already exists: %s", DEMO_TENANT_ID)

        # 2. Config Check / Creation
        stmt = select(TenantConfigDb).where(TenantConfigDb.tenant_id == DEMO_TENANT_ID)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            logger.info("Initializing tenant configuration...")
            config = TenantConfigDb(
                tenant_id=DEMO_TENANT_ID,
                system_prompt_template="You are the Retriever Enterprise AI Copilot. Assist engineers with technical queries.",
                hybrid_alpha=0.7,
                reranker_engine="colbert",
            )
            session.add(config)
            await session.flush()

        # 3. Master Demo API Key Check / Creation
        stmt = select(ApiKeyDb).where(ApiKeyDb.key_hash == DEMO_KEY_HASH)
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            logger.info("Registering master demo API key: %s...", DEMO_KEY_PREFIX)
            api_key = ApiKeyDb(
                tenant_id=DEMO_TENANT_ID,
                name="Master Demo Key",
                prefix=DEMO_KEY_PREFIX,
                key_hash=DEMO_KEY_HASH,
                role="admin",
                status="active",
            )
            session.add(api_key)
            await session.flush()
        else:
            logger.info("Master demo API key is active.")

        # 4. Document & Chunks Check / Creation
        stmt = select(DocumentDb).where(
            DocumentDb.tenant_id == DEMO_TENANT_ID,
            DocumentDb.filename == "retriever_architecture_whitepaper.md",
        )
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()

        if not doc:
            logger.info("Seeding sample engineering whitepaper document...")
            doc_id = uuid.uuid4()
            full_content = "\n\n".join(c["content"] for c in SAMPLE_CHUNKS)
            doc = DocumentDb(
                document_id=doc_id,
                tenant_id=DEMO_TENANT_ID,
                filename="retriever_architecture_whitepaper.md",
                file_hash=hashlib.sha256(full_content.encode()).hexdigest(),
                storage_path=f"storage/documents/{DEMO_TENANT_ID}/{doc_id}.md",
                file_size=len(full_content.encode()),
                mime_type="text/markdown",
                status="INDEXED",
                tags=["whitepaper", "architecture", "enterprise"],
            )
            session.add(doc)
            await session.flush()

            logger.info("Generating embeddings and indexing %d chunks...", len(SAMPLE_CHUNKS))
            for idx, item in enumerate(SAMPLE_CHUNKS):
                chunk_vector = await generate_embedding(item["content"], ollama_url)
                chunk = DocumentChunkDb(
                    chunk_id=uuid.uuid4(),
                    document_id=doc.document_id,
                    tenant_id=DEMO_TENANT_ID,
                    chunk_index=idx,
                    content=f"## {item['title']}\n\n{item['content']}",
                    embedding=chunk_vector,
                    meta_info={"title": item["title"], "tags": item["tags"]},
                )
                session.add(chunk)

            await session.flush()
            logger.info("Sample whitepaper indexed successfully.")
        else:
            logger.info("Sample whitepaper document already indexed.")

        await session.commit()
        logger.info("Demo environment seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed_database())
