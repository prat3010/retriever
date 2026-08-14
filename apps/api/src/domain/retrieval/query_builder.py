from typing import Any

from src.domain.abstractions.config import TenantConfiguration
from src.domain.abstractions.retrieval import SearchQuery


def build_search_query(
    tenantId: str,
    tenant_config: TenantConfiguration,
    payload: Any,
    user_id: str | None = None,
    user_role: str | None = None,
) -> SearchQuery:
    raw_user_id = user_id or getattr(payload, "user_id", None)
    raw_user_role = user_role or getattr(payload, "user_role", None)
    clean_user_id = raw_user_id if isinstance(raw_user_id, str) else None
    clean_user_role = raw_user_role if isinstance(raw_user_role, str) else None


    return SearchQuery(
        query=payload.query,
        tenant_id=tenantId,
        collection_id=getattr(payload, "collection_id", None),
        user_id=clean_user_id,
        user_role=clean_user_role,

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

