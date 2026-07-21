from src.domain.abstractions.config import (
    CorrectiveRetrievalSettings,
    TenantConfiguration,
)
from src.domain.abstractions.inference import InferenceResponse
from src.domain.abstractions.retrieval import CorrectiveRetrievalProvider, SearchQuery
from src.domain.inference.orchestrator import InferenceOrchestrator
from src.domain.retrieval.search_service import HybridSearchService


class CorrectiveRetrievalService:

    def __init__(
        self,
        search_service: HybridSearchService,
        orchestrator: InferenceOrchestrator,
        corrective_provider: CorrectiveRetrievalProvider,
    ) -> None:
        self.search_service = search_service
        self.orchestrator = orchestrator
        self.corrective_provider = corrective_provider

    async def generate_with_correction(
        self,
        tenant_id: str,
        session_id: str,
        query: str,
        search_query: SearchQuery,
        tenant_config: TenantConfiguration,
        user_id: str | None = None,
        role: str | None = None,
        key_id: str | None = None,
        system_prompt_name: str = "default",
    ) -> InferenceResponse:
        settings: CorrectiveRetrievalSettings = tenant_config.corrective_retrieval_settings

        search_resp = await self.search_service.search(search_query)
        response = await self.orchestrator.generate(
            tenant_id=tenant_id,
            session_id=session_id,
            query=query,
            context_chunks=search_resp.results,
            tenant_config=tenant_config,
            user_id=user_id,
            role=role,
            key_id=key_id,
            system_prompt_name=system_prompt_name,
        )

        for _ in range(max(0, settings.max_retrieval_rounds - 1)):
            try:
                decision = await self.corrective_provider.evaluate_response(
                    query=query,
                    response=response.content,
                    context_chunks=search_resp.results,
                )
            except Exception:
                break
            if not decision.needs_re_retrieval:
                break
            if decision.confidence_score >= settings.confidence_threshold:
                break

            refined_query = decision.reformulated_query or query
            refined_search_query = search_query.model_copy(update={"query": refined_query})
            search_resp = await self.search_service.search(refined_search_query)
            response = await self.orchestrator.generate(
                tenant_id=tenant_id,
                session_id=session_id,
                query=query,
                context_chunks=search_resp.results,
                tenant_config=tenant_config,
                user_id=user_id,
                role=role,
                key_id=key_id,
                system_prompt_name=system_prompt_name,
            )

        return response
