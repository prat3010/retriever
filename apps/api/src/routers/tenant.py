import json
import logging
import time
from typing import Any

import openai
from fastapi import APIRouter, Depends, HTTPException, Query, Security, status

from src.adapters.api.security import (
    verify_admin_key,
    verify_scopes,
    verify_tenant_isolation,
    verify_tenant_or_admin,
)
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from src.config import settings
from src.container import (
    audit_logger,
    config_service,
    identity_provider,
    inference_orchestrator,
    tenant_registry,
)
from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.inference import ChatMessage, InferenceRequest
from src.domain.clustering.abstractions import (
    KnowledgeGapReport,
    TopicClusteringRequest,
    TopicClusteringResponse,
)
from src.domain.projection.abstractions import (
    EmbeddingProjectionRequest,
    EmbeddingProjectionResponse,
)
from src.schemas.admin import (
    ApiKeyCreatedResponse,
    CreateApiKeyRequest,
    ValidateKeyRequest,
    ValidateKeyResponse,
)
from src.schemas.graph import (
    GraphQueryRequest,
    GraphQueryResponse,
    GraphSummaryResponse,
)
from src.schemas.intent import (
    ClassifyIntentRequest,
    ClassifyIntentResponse,
    ScopingIntentResult,
)
from src.schemas.tenant import CreateTenantRequest, TenantListItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["Tenants"])



@router.post(
    "/tenants",
    status_code=status.HTTP_201_CREATED,
    response_model=TenantListItem,
    dependencies=[Depends(verify_admin_key)],
)
async def create_tenant(
    payload: CreateTenantRequest,
) -> TenantListItem:
    tenant = await tenant_registry.create_tenant(
        name=payload.name,
        tier=payload.tier,
        isolation_level=payload.isolation_level,
    )
    await audit_logger.write(tenant.tenant_id, "tenant.created", f"Tenant '{payload.name}' created")
    return TenantListItem(
        tenantId=tenant.tenant_id,
        name=tenant.name,
        status=tenant.status,
        tier=tenant.tier,
        createdAt=tenant.created_at,
    )


@router.post(
    "/config/validate-key",
    status_code=status.HTTP_200_OK,
    response_model=ValidateKeyResponse,
    dependencies=[Depends(verify_admin_key)],
)
async def validate_api_key(
    payload: ValidateKeyRequest,
) -> ValidateKeyResponse:
    try:
        api_key = payload.api_key or settings.OPENAI_API_KEY
        if not api_key:
            return ValidateKeyResponse(valid=False, error="No API key provided and no server-wide key found.")
        kwargs = {"api_key": api_key}
        base_url = payload.base_url
        if not base_url and payload.provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        elif not base_url and payload.provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.AsyncOpenAI(**kwargs)
        await client.chat.completions.create(
            model=payload.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            timeout=10
        )
        return ValidateKeyResponse(valid=True)
    except openai.AuthenticationError as ae:
        return ValidateKeyResponse(valid=False, error=f"Authentication Error: {ae.message}")
    except Exception as e:
        return ValidateKeyResponse(valid=False, error=str(e))


@router.put(
    "/config/global",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_admin_key)],
)
async def update_global_config(
    payload: TenantConfiguration,
) -> dict[str, str]:
    await config_service.update_global_config(payload)
    await audit_logger.write("global", "config.updated", "Global configuration updated")
    return {"status": "updated", "scope": "global"}


@router.get(
    "/config/global",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_admin_key)],
)
async def get_global_config() -> TenantConfiguration:
    config = await config_service.get_global_config()
    return config.redact_secrets()


@router.put(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def update_tenant_config(
    tenantId: str,
    payload: TenantConfiguration,
) -> dict[str, str]:
    await config_service.update_tenant_config(tenantId, payload)
    return {"tenantId": tenantId, "status": "updated"}


@router.get(
    "/tenants/{tenantId}/config",
    status_code=status.HTTP_200_OK,
    response_model=TenantConfiguration,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_tenant_config(tenantId: str) -> TenantConfiguration:
    config = await config_service.get_tenant_config(tenantId)
    return config.redact_secrets()


@router.post(
    "/tenants/{tenantId}/api-keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiKeyCreatedResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def generate_api_key(
    tenantId: str,
    payload: CreateApiKeyRequest,
) -> ApiKeyCreatedResponse:
    raw_key, metadata = await identity_provider.create_api_key(
        tenant_id=tenantId,
        name=payload.name,
        expires_in_days=payload.expires_in_days,
        role=payload.role,
    )
    return ApiKeyCreatedResponse(
        apiKey=raw_key,
        keyId=metadata.key_id,
        tenantId=metadata.tenant_id,
        prefix=metadata.prefix,
        role=metadata.role,
        status=metadata.status,
        expiresAt=metadata.expires_at,
    )


@router.post(
    "/tenants/{tenantId}/clusters/topics",
    status_code=status.HTTP_200_OK,
    response_model=TopicClusteringResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_tenant_topic_clusters(
    tenantId: str,
    payload: TopicClusteringRequest | None = None,
) -> TopicClusteringResponse:
    """Execute unsupervised HDBSCAN clustering and return dynamic semantic topic models."""
    from src.container import document_repository, topic_clusterer

    req = payload or TopicClusteringRequest()
    chunks_with_embeddings = await document_repository.get_tenant_chunks_with_embeddings(tenantId)

    chunk_ids = [c.chunk_id for c, _ in chunks_with_embeddings]
    chunk_texts = [c.content for c, _ in chunks_with_embeddings]
    embeddings = [emb for _, emb in chunks_with_embeddings if emb]

    return topic_clusterer.cluster_chunks(
        tenant_id=tenantId,
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        embeddings=embeddings,
        request=req,
    )


@router.get(
    "/tenants/{tenantId}/clusters/knowledge-gaps",
    status_code=status.HTTP_200_OK,
    response_model=KnowledgeGapReport,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def get_tenant_knowledge_gaps(
    tenantId: str,
) -> KnowledgeGapReport:
    """Detect orphaned chunks, sparse clusters, and synthesize vault coverage diagnostics."""
    from src.container import document_repository, topic_clusterer

    chunks_with_embeddings = await document_repository.get_tenant_chunks_with_embeddings(tenantId)

    chunk_ids = [c.chunk_id for c, _ in chunks_with_embeddings]
    chunk_texts = [c.content for c, _ in chunks_with_embeddings]
    embeddings = [emb for _, emb in chunks_with_embeddings if emb]

    clustering_res = topic_clusterer.cluster_chunks(
        tenant_id=tenantId,
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        embeddings=embeddings,
        request=TopicClusteringRequest(min_cluster_size=2),
    )

    chunk_text_dict = dict(zip(chunk_ids, chunk_texts, strict=False))
    return topic_clusterer.analyze_knowledge_gaps(
        tenant_id=tenantId,
        clustering_result=clustering_res,
        chunk_texts=chunk_text_dict,
    )


@router.post(
    "/tenants/{tenantId}/embeddings/project",
    status_code=status.HTTP_200_OK,
    response_model=EmbeddingProjectionResponse,
    dependencies=[Depends(verify_tenant_or_admin)],

)
async def project_tenant_embeddings(
    tenantId: str,
    payload: EmbeddingProjectionRequest | None = None,
) -> EmbeddingProjectionResponse:
    """Project high-dimensional embeddings into 2D/3D Cartesian coordinates with topic clusters."""
    from src.container import document_repository, embedding_projector, topic_clusterer

    req = payload or EmbeddingProjectionRequest()
    chunks_with_embeddings = await document_repository.get_tenant_chunks_with_embeddings(tenantId)

    chunk_ids = [c.chunk_id for c, _ in chunks_with_embeddings]
    chunk_texts = [c.content for c, _ in chunks_with_embeddings]
    document_ids = [c.document_id for c, _ in chunks_with_embeddings]
    document_titles = [
        c.metadata.get("file_name", c.metadata.get("title", "Document"))
        for c, _ in chunks_with_embeddings
    ]
    embeddings = [emb for _, emb in chunks_with_embeddings if emb]

    # Pre-cluster to assign topic clusters and labels
    cluster_ids = None
    cluster_labels = None
    if len(chunk_ids) > 0 and len(embeddings) > 0:
        cluster_res = topic_clusterer.cluster_chunks(
            tenant_id=tenantId,
            chunk_ids=chunk_ids,
            chunk_texts=chunk_texts,
            embeddings=embeddings,
            request=TopicClusteringRequest(min_cluster_size=2),
        )
        chunk_to_topic = {}
        for topic in cluster_res.topics:
            for cid in topic.chunk_ids:
                chunk_to_topic[cid] = topic.topic_id
        cluster_ids = [chunk_to_topic.get(cid, -1) for cid in chunk_ids]
        cluster_labels = {topic.topic_id: topic.label for topic in cluster_res.topics}

    return embedding_projector.project_embeddings(
        tenant_id=tenantId,
        chunk_ids=chunk_ids,
        chunk_texts=chunk_texts,
        document_ids=document_ids,
        document_titles=document_titles,
        embeddings=embeddings,
        cluster_ids=cluster_ids,
        cluster_labels=cluster_labels,
        request=req,
    )


# ---------------------------------------------------------------------------
# Tenant-Scoped Knowledge Graph Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/tenants/{tenantId}/graph",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=GraphSummaryResponse,
)
async def get_tenant_knowledge_graph_summary(tenantId: str) -> GraphSummaryResponse:
    """Fetch Knowledge Graph metrics and active storage engine for the tenant."""
    from src.container import container

    summary = await container.graph_repository.get_graph_summary(tenantId)
    return GraphSummaryResponse(
        tenant_id=tenantId,
        total_triples=summary.get("total_triples", 0),
        unique_entities=summary.get("unique_entities", 0),
        storage_engine=summary.get("storage_engine", "postgres"),
        neo4j_status=summary.get("neo4j_status"),
    )


@router.post(
    "/tenants/{tenantId}/graph/query",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
    response_model=GraphQueryResponse,
)
async def query_tenant_knowledge_graph(tenantId: str, payload: GraphQueryRequest) -> GraphQueryResponse:
    """Execute recursive multi-hop entity traversal on tenant's knowledge graph."""
    from src.container import container

    res = await container.graph_repository.search_triples(
        tenant_id=tenantId,
        entity=payload.entity,
        max_hops=payload.max_hops,
    )
    return GraphQueryResponse(
        root_entity=res.root_entity,
        max_hops=res.max_hops,
        triples=res.triples,
        connected_entities=res.connected_entities,
    )


@router.delete(
    "/tenants/{tenantId}/graph/triples/{tripleId}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def delete_tenant_knowledge_graph_triple(tenantId: str, tripleId: str) -> dict[str, str]:
    """Delete an individual triple from tenant's knowledge graph."""
    from src.container import container

    success = await container.graph_repository.delete_triple(
        tenant_id=tenantId,
        triple_id=tripleId,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Triple not found or could not be deleted.",
        )
    return {"status": "success", "message": f"Triple {tripleId} deleted."}


# ---------------------------------------------------------------------------
# Tenant-Scoped Semantic Cache Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/tenants/{tenantId}/cache/purge",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def purge_tenant_semantic_cache(tenantId: str) -> dict[str, Any]:
    """Purge all cached search embeddings for the tenant workspace."""
    from src.container import semantic_cache

    deleted_count = await semantic_cache.purge_tenant_cache(tenantId)
    return {"status": "success", "purged": True, "deleted_count": deleted_count}


@router.get(
    "/tenants/{tenantId}/cache/stats",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_tenant_semantic_cache_stats(tenantId: str) -> dict[str, Any]:
    """Fetch active semantic vector cache statistics for the tenant workspace."""
    from src.container import semantic_cache

    stats = await semantic_cache.get_tenant_cache_stats(tenantId)
    return {"status": "success", **stats}


# ---------------------------------------------------------------------------
# Tenant-Scoped Online Evaluation Telemetry
# ---------------------------------------------------------------------------


@router.get(
    "/tenants/{tenantId}/evaluations/summary",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_or_admin)],
)
async def get_tenant_online_evaluation_summary(tenantId: str) -> Any:
    """Fetch aggregated live evaluation metrics (faithfulness, precision, hallucination index)."""
    from src.container import online_eval_repo

    return await online_eval_repo.get_online_summary(tenantId)


# ---------------------------------------------------------------------------
# Tenant-Scoped CPQ Scoping Intent Classification (M85.11)
# ---------------------------------------------------------------------------


@router.post(
    "/tenants/{tenantId}/intent/classify",
    status_code=status.HTTP_200_OK,
    response_model=ClassifyIntentResponse,
    dependencies=[
        Depends(verify_tenant_or_admin),
        Depends(rate_limit(scope="intent", max_requests=30)),
    ],
)
async def classify_scoping_intent(
    tenantId: str,
    payload: ClassifyIntentRequest,
) -> ClassifyIntentResponse:
    """Classify natural language project description into structured CPQ architecture parameters using LLM."""
    start_time = time.perf_counter()
    tenant_config = await config_service.get_tenant_config(tenantId)

    json_schema = ScopingIntentResult.model_json_schema()
    system_prompt = (
        "You are an expert Solutions Architect and CPQ Intent Classifier. "
        "Analyze the user's project description and map it to software architecture parameters. "
        "Return ONLY a JSON object matching this schema:\n"
        f"{json.dumps(json_schema)}\n"
        "Valid feature_ids: 'auth', 'admin', 'payments', 'email', 'cms', 'search', 'blog', "
        "'ai_rag', 'ai_voice_agent', 'ai_vision_ocr', 'ai_agents', 'integrations', 'commerce', 'lms', 'analytics', 'seo', 'multi_language'. "
        "Valid base_engine_id: 'landing' (single-page waitlist/landing), 'multipage' (multi-page/e-commerce), 'saas' (web app/portal/dashboard/RAG). "
        "Output pure valid JSON only without markdown formatting."
    )

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=f"Project Scope: {payload.prompt}"),
    ]

    model_override = payload.model or tenant_config.ai_provider.model or "meta-llama/llama-3.3-70b-instruct"
    config: dict[str, Any] = {"model": model_override}

    try:
        response = await inference_orchestrator.llm.generate(
            InferenceRequest(messages=messages, temperature=0.1, json_schema=json_schema),
            config,
        )
        raw = response.content.strip()
        raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed_dict = json.loads(raw)
        intent_result = ScopingIntentResult(**parsed_dict)
    except Exception as exc:
        logger.warning(f"Structured intent classification fallback due to error: {exc}")
        p_lower = payload.prompt.lower()
        is_rag = any(k in p_lower for k in ["rag", "knowledge base", "vector", "citation", "semantic search"])
        is_voice = any(k in p_lower for k in ["voice", "speech", "calling bot", "elevenlabs"])
        is_ecom = any(k in p_lower for k in ["store", "ecommerce", "e-commerce", "shop", "cart"])
        is_landing = any(k in p_lower for k in ["landing page", "waitlist", "teaser", "single page"])

        if is_voice:
            intent_result = ScopingIntentResult(
                archetype_id="voice_ai_agent_app",
                base_engine_id="saas",
                feature_ids=["ai_voice_agent", "ai_rag", "auth", "admin", "email"],
                brand_asset_id="comprehensive",
                maintenance_plan_id="premium",
                suggested_timeline="4 to 5 Weeks",
                confidence_score=0.92,
                summary_rationale="Configured with conversational Voice AI agent, Retriever RAG knowledge base, and audio synthesis.",
                retriever_engine_recommended=True,
            )
        elif is_rag:
            intent_result = ScopingIntentResult(
                archetype_id="ai_rag_app",
                base_engine_id="saas",
                feature_ids=["ai_rag", "auth", "admin", "search", "email"],
                brand_asset_id="basic",
                maintenance_plan_id="premium",
                suggested_timeline="4 Weeks",
                confidence_score=0.95,
                summary_rationale="Configured with Retriever Enterprise RAG engine, pgvector semantic indexing, and role-based admin center.",
                retriever_engine_recommended=True,
            )
        elif is_ecom:
            intent_result = ScopingIntentResult(
                archetype_id="ecommerce",
                base_engine_id="multipage",
                feature_ids=["commerce", "payments", "email"],
                brand_asset_id="comprehensive",
                maintenance_plan_id="standard",
                suggested_timeline="3 to 4 Weeks",
                confidence_score=0.90,
                summary_rationale="Configured for headless e-commerce storefront with product catalog and payment checkout.",
                retriever_engine_recommended=False,
            )
        elif is_landing:
            intent_result = ScopingIntentResult(
                archetype_id="landing_page",
                base_engine_id="landing",
                feature_ids=["email"],
                brand_asset_id="basic",
                maintenance_plan_id="standard",
                suggested_timeline="1 Week",
                confidence_score=0.92,
                summary_rationale="High-converting single-page Landing Core Engine with lead capture.",
                retriever_engine_recommended=False,
            )
        else:
            intent_result = ScopingIntentResult(
                archetype_id="saas_app",
                base_engine_id="saas",
                feature_ids=["auth", "admin", "payments", "email"],
                brand_asset_id="basic",
                maintenance_plan_id="standard",
                suggested_timeline="4 Weeks",
                confidence_score=0.85,
                summary_rationale="Configured with full-stack SaaS platform architecture with authentication, billing, and admin center.",
                retriever_engine_recommended=False,
            )
        provider_name = tenant_config.ai_provider.provider_name or "fallback"
        input_tokens = 0
        output_tokens = 0
        finish_reason = "fallback"
    else:
        provider_name = tenant_config.ai_provider.provider_name
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        finish_reason = response.finish_reason

    latency_ms = max(1, int((time.perf_counter() - start_time) * 1000))

    return ClassifyIntentResponse(
        success=True,
        data=intent_result,
        model=model_override,
        provider=finish_reason or provider_name,
        inputTokens=input_tokens,
        outputTokens=output_tokens,
        latencyMs=latency_ms,
    )


# ── Milestone 83: Tenant Security Anomalies ─────────────────────────────────


@router.get(
    "/tenants/{tenantId}/telemetry/anomalies",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation)],
)
async def get_tenant_telemetry_anomalies(
    tenantId: str,
    risk_level: str | None = Query(None, description="Filter by risk level (LOW, MEDIUM, HIGH, CRITICAL)"),
    status: str | None = Query(None, description="Filter by status (active, resolved)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Retrieve security anomaly events scoped to the authenticated tenant."""
    from src.container import anomaly_sentinel_service

    items, total = await anomaly_sentinel_service.list_anomalies(
        tenant_id=tenantId,
        risk_level=risk_level,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {
        "tenant_id": tenantId,
        "total": total,
        "items": items,
        "limit": limit,
        "offset": offset,
    }





