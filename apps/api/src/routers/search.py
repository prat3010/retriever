"""Search routes."""
from fastapi import APIRouter, Depends, Security, status

from src.adapters.api.security import verify_scopes, verify_tenant_isolation
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from src.container import config_service, search_service
from src.domain.abstractions.retrieval import SearchQuery
from src.schemas.search import (
    SearchMetaResponse,
    SearchRequest,
    SearchResponseDto,
    SearchResultItem,
)

router = APIRouter(tags=["Search"])


@router.post(
    "/v1/tenants/{tenantId}/search",
    status_code=status.HTTP_200_OK,
    response_model=SearchResponseDto,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"]), Depends(rate_limit(scope="search", max_requests=120))],
)
async def search_documents(
    tenantId: str,
    payload: SearchRequest,
) -> SearchResponseDto:
    """Execute hybrid search across tenant document vectors and keyword indexes."""
    tenant_config = await config_service.get_tenant_config(tenantId)

    query = SearchQuery(
        query=payload.query,
        tenant_id=tenantId,
        top_k=payload.limit,
        filters=payload.filters,
        tags=payload.tags,
        enable_hybrid=tenant_config.feature_flags.enable_hybrid_search,
        enable_reranking=tenant_config.feature_flags.enable_reranking,
        enable_bm25=tenant_config.bm25_settings.enable_bm25,
        enable_mmr=tenant_config.mmr_settings.enable_mmr,
        enable_query_rewriting=tenant_config.feature_flags.enable_query_rewriting,
        rrf_k=tenant_config.retrieval_settings.rrf_k,
        reranking_threshold=tenant_config.retrieval_settings.reranking_threshold,
        rerank_candidate_multiplier=tenant_config.retrieval_settings.rerank_candidate_multiplier,
        enable_web_search=tenant_config.feature_flags.enable_web_search,
        web_search_provider=tenant_config.retrieval_settings.web_search_provider,
        web_search_api_key=tenant_config.retrieval_settings.web_search_api_key,
        web_search_threshold=tenant_config.retrieval_settings.web_search_threshold,
        web_search_max_results=tenant_config.retrieval_settings.web_search_max_results,
        enable_self_query=tenant_config.feature_flags.enable_self_query,
        enable_query_intent=tenant_config.feature_flags.enable_query_intent,
    )

    response = await search_service.search(query)
    return SearchResponseDto(
        query=response.query,
        results=[
            SearchResultItem(
                chunkId=r.chunk_id,
                documentId=r.document_id,
                content=r.content,
                score=r.score,
                metadata=r.metadata,
            )
            for r in response.results
        ],
        searchMeta=SearchMetaResponse(
            strategy=response.search_meta.strategy,
            totalCandidates=response.search_meta.total_candidates,
            returnedResults=response.search_meta.returned_results,
            durationMs=response.search_meta.duration_ms,
        ),
    )
