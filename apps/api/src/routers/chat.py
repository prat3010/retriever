"""Chat and session routes."""
import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Security, status
from fastapi.responses import StreamingResponse

from src.adapters.api.security import (
    get_current_user,
    get_current_user_id,
    verify_scopes,
    verify_tenant_isolation,
)
from src.adapters.telemetry.rate_limiter_dep import rate_limit
from src.container import (
    config_service,
    corrective_service,
    feedback_repo,
    inference_orchestrator,
    search_service,
    session_repo,
)
from src.domain.abstractions.identity import UserContext
from src.domain.abstractions.inference import ChatMessageFeedback
from src.domain.guardrails import apply_input_guardrails as _apply_input_guardrails
from src.domain.inference.citation_formatter import (
    format_citations as _format_citations,
)
from src.domain.retrieval.experiment_service import apply_overrides, assign_variant
from src.domain.retrieval.query_builder import build_search_query as _build_search_query
from src.schemas.chat import (
    ChatMessageRequest,
    CreateSessionResponse,
    FeedbackSubmitRequest,
)

router = APIRouter(tags=["Chat"])


@router.post(
    "/v1/tenants/{tenantId}/chat/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateSessionResponse,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"])],
)
async def create_chat_session(
    tenantId: str,
    user_id: str | None = Depends(get_current_user_id),
) -> CreateSessionResponse:
    """Create a new chat session for grounded inference."""
    session = await inference_orchestrator.create_session(tenantId, user_id)
    return CreateSessionResponse(
        sessionId=session.session_id,
        createdAt=session.created_at,
    )


@router.post(
    "/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:write"]), Depends(rate_limit(scope="chat", max_requests=30))],
)
async def send_chat_message(
    tenantId: str,
    sessionId: str,
    payload: ChatMessageRequest,
    user_id: str | None = Depends(get_current_user_id),
    user_context: UserContext = Depends(get_current_user),
    x_llm_key: str | None = Header(None, alias="X-LLM-Key"),
    x_llm_provider: str | None = Header(None, alias="X-LLM-Provider"),
):
    session = await inference_orchestrator.get_session(sessionId, tenantId)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session_user_id = getattr(session, "user_id", None)
    if session_user_id and isinstance(session_user_id, str) and session_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Forbidden: You do not own this chat session."
        )

    caller_role = user_context.roles[0] if user_context.roles else None
    caller_key_id = user_context.key_id

    tenant_config = await config_service.get_tenant_config(tenantId)

    experiment_id = None
    experiment_variant = None
    if tenant_config.experiments:
        for exp in tenant_config.experiments:
            variant = assign_variant(user_id, exp)
            if variant:
                tenant_config = apply_overrides(tenant_config, variant)
                experiment_id = exp.id
                experiment_variant = variant.id
                break

    payload.query = await _apply_input_guardrails(tenant_config, payload.query)

    if x_llm_key:
        tenant_config.ai_provider.api_key = x_llm_key
    if x_llm_provider:
        tenant_config.ai_provider.provider_name = x_llm_provider

    search_query = _build_search_query(tenantId, tenant_config, payload)
    search_response = await search_service.search(search_query)

    citation_template = tenant_config.retrieval_settings.citation_template

    if not payload.stream:
        if tenant_config.corrective_retrieval_settings.enable_corrective_retrieval:
            response = await corrective_service.generate_with_correction(
                tenant_id=tenantId,
                session_id=sessionId,
                query=payload.query,
                search_query=search_query,
                tenant_config=tenant_config,
                user_id=user_id,
                role=caller_role,
                key_id=caller_key_id,
                system_prompt_name=payload.system_prompt_name,
            )
        else:
            response = await inference_orchestrator.generate(
                tenant_id=tenantId,
                session_id=sessionId,
                query=payload.query,
                context_chunks=search_response.results,
                tenant_config=tenant_config,
                user_id=user_id,
                role=caller_role,
                key_id=caller_key_id,
                system_prompt_name=payload.system_prompt_name,
                experiment_id=experiment_id,
                experiment_variant=experiment_variant,
            )
        formatted_content = _format_citations(response.content, search_response.results, citation_template)
        return {
            "content": formatted_content,
            "usage": response.usage.model_dump(),
            "finish_reason": response.finish_reason,
        }

    async def event_stream() -> AsyncGenerator[str, None]:
        logger = logging.getLogger("api")
        buffer = ""
        try:
            async for event in inference_orchestrator.generate_stream(
                tenant_id=tenantId,
                session_id=sessionId,
                query=payload.query,
                context_chunks=search_response.results,
                tenant_config=tenant_config,
                user_id=user_id,
                role=caller_role,
                key_id=caller_key_id,
                system_prompt_name=payload.system_prompt_name,
                experiment_id=experiment_id,
                experiment_variant=experiment_variant,
            ):
                if event.get("event") == "token":
                    delta = event.get("delta", "")
                    buffer += delta
                    buffer = _format_citations(buffer, search_response.results, citation_template)

                    last_bracket = buffer.rfind("[")
                    if last_bracket != -1 and ("source".startswith(buffer[last_bracket+1:last_bracket+8].lower()) or len(buffer) - last_bracket < 50):
                        safe_to_yield = buffer[:last_bracket]
                        buffer = buffer[last_bracket:]
                    else:
                        safe_to_yield = buffer
                        buffer = ""

                    if safe_to_yield:
                        event["delta"] = safe_to_yield
                        yield f"data: {json.dumps(event)}\n\n"
                else:
                    if buffer and event.get("event") == "done":
                        yield f"data: {json.dumps({'event': 'token', 'delta': buffer})}\n\n"
                        buffer = ""
                    yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected for session {sessionId} on tenant {tenantId}.")
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def list_session_messages(
    tenantId: str,
    sessionId: str,
    limit: int = 50,
    cursor: str | None = None,
    user_id: str | None = Depends(get_current_user_id),
) -> Any:
    """Retrieve message history for a chat session with cursor-based pagination."""
    session = await inference_orchestrator.get_session(sessionId, tenantId)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    session_user_id = getattr(session, "user_id", None)
    if session_user_id and isinstance(session_user_id, str) and session_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Forbidden: You do not own this chat session."
        )

    items, next_cursor, has_more = await session_repo.get_messages_cursor(
        tenant_id=tenantId, session_id=sessionId, limit=limit, cursor=cursor
    )

    return {
        "items": [
            {
                "messageId": m.message_id,
                "sessionId": m.session_id,
                "tenantId": m.tenant_id,
                "role": m.role,
                "content": m.content,
                "name": m.name,
                "createdAt": m.created_at,
            }
            for m in items
        ],
        "pagination": {
            "nextCursor": next_cursor,
            "limit": limit,
            "hasMore": has_more,
        }
    }


@router.post(
    "/v1/tenants/{tenantId}/chat/sessions/{sessionId}/messages/{messageId}/feedback",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_tenant_isolation), Security(verify_scopes, scopes=["document:read"])],
)
async def submit_message_feedback(
    tenantId: str,
    sessionId: str,
    messageId: str,
    payload: FeedbackSubmitRequest,
    user_id: str | None = Depends(get_current_user_id),
) -> Any:
    """Submit or update user feedback (thumbs up/down + optional comments) for a chat response."""
    session = await inference_orchestrator.get_session(sessionId, tenantId)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    msg = await session_repo.get_message(tenantId, sessionId, messageId)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found in this session.")

    feedback = ChatMessageFeedback(
        tenant_id=tenantId,
        message_id=messageId,
        user_id=user_id,
        rating=payload.rating,
        feedback_text=payload.feedback_text,
        scores=payload.scores,
    )
    await feedback_repo.submit_feedback(feedback)

    return {"status": "success", "message": "Feedback submitted successfully."}
