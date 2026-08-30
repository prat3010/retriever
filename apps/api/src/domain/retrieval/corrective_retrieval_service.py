from src.domain.abstractions.config import (
    CorrectiveRetrievalSettings,
    TenantConfiguration,
)
from src.domain.abstractions.inference import InferenceResponse
from src.domain.abstractions.retrieval import (
    CorrectiveRetrievalDecision,
    CorrectiveRetrievalProvider,
    SearchQuery,
    SearchResult,
)
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

    async def prepare_crag_context(
        self,
        tenant_id: str,
        query: str,
        search_query: SearchQuery,
        tenant_config: TenantConfiguration,
    ) -> tuple[list[SearchResult], CorrectiveRetrievalDecision]:
        """Execute pre-generation CRAG evaluation, query reformulation, web search fallback, and document refinement."""
        from src.domain.retrieval.document_refiner import refine_search_results

        # 1. Initial retrieval
        initial_resp = await self.search_service.search(search_query)
        candidates = initial_resp.results

        # 2. Evaluate candidate retrieval confidence
        try:
            decision = await self.corrective_provider.evaluate_candidates(
                query=query,
                candidates=candidates,
                upper_threshold=tenant_config.corrective_retrieval_settings.confidence_threshold,
                lower_threshold=0.40,
            )
        except Exception:
            decision = CorrectiveRetrievalDecision(
                status="CORRECT",
                confidence_score=0.8,
                needs_re_retrieval=False,
                needs_web_search=False,
            )

        # 3. Branch execution
        if decision.status == "CORRECT":
            # Direct document refinement (strip boilerplate sentences)
            refined = refine_search_results(query, candidates)
            decision.refined_chunks = refined
            return refined, decision

        elif decision.status == "AMBIGUOUS":
            # Knowledge gap: reformulate query and trigger supplementary search / web search
            search_q_str = decision.reformulated_query or query
            sec_query = search_query.model_copy(update={"query": search_q_str, "enable_web_search": True})
            sec_resp = await self.search_service.search(sec_query)
            # Combine initial candidates and secondary/web results
            seen_ids = {c.chunk_id for c in candidates}
            combined = list(candidates)
            for r in sec_resp.results:
                if r.chunk_id not in seen_ids:
                    seen_ids.add(r.chunk_id)
                    combined.append(r)
            refined = refine_search_results(query, combined)
            decision.refined_chunks = refined
            return refined, decision

        else:  # INCORRECT
            # Suppress ungrounded internal chunks and execute pure web search fallback
            search_q_str = decision.reformulated_query or query
            web_fallback_query = search_query.model_copy(update={"query": search_q_str, "enable_web_search": True})
            web_resp = await self.search_service.search(web_fallback_query)
            refined = refine_search_results(query, web_resp.results)
            decision.refined_chunks = refined
            return refined, decision

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
        experiment_id: str | None = None,
        experiment_variant: str | None = None,
    ) -> InferenceResponse:
        settings: CorrectiveRetrievalSettings = tenant_config.corrective_retrieval_settings
        if not settings.enable_corrective_retrieval:
            search_resp = await self.search_service.search(search_query)
            return await self.orchestrator.generate(
                tenant_id=tenant_id,
                session_id=session_id,
                query=query,
                context_chunks=search_resp.results,
                tenant_config=tenant_config,
                user_id=user_id,
                role=role,
                key_id=key_id,
                system_prompt_name=system_prompt_name,
                experiment_id=experiment_id,
                experiment_variant=experiment_variant,
            )

        search_resp = await self.search_service.search(search_query)
        context_chunks = search_resp.results

        response = await self.orchestrator.generate(
            tenant_id=tenant_id,
            session_id=session_id,
            query=query,
            context_chunks=context_chunks,
            tenant_config=tenant_config,
            user_id=user_id,
            role=role,
            key_id=key_id,
            system_prompt_name=system_prompt_name,
            experiment_id=experiment_id,
            experiment_variant=experiment_variant,
        )

        for _ in range(max(0, settings.max_retrieval_rounds - 1)):
            try:
                decision = await self.corrective_provider.evaluate_response(
                    query=query,
                    response=response.content,
                    context_chunks=context_chunks,
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
            context_chunks = search_resp.results
            response = await self.orchestrator.generate(
                tenant_id=tenant_id,
                session_id=session_id,
                query=query,
                context_chunks=context_chunks,
                tenant_config=tenant_config,
                user_id=user_id,
                role=role,
                key_id=key_id,
                system_prompt_name=system_prompt_name,
                experiment_id=experiment_id,
                experiment_variant=experiment_variant,
            )

        return response
