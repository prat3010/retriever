from typing import Any

from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.retrieval import SearchQuery


def build_search_query(
    tenantId: str,
    tenant_config: TenantConfiguration,
    payload: Any,
) -> SearchQuery:
    return SearchQuery(
        query=payload.query,
        tenant_id=tenantId,
        top_k=tenant_config.retrieval_settings.top_k,
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
