"""Ecosystem integrations routes for Slack, Chrome Extension, and Cloud Drives."""
import io
import logging
import os
import time
import zipfile
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)

from src.config import settings
from src.container import (
    inference_orchestrator,
    search_service,
    slack_service,
)
from src.domain.abstractions.inference import ChatMessage, InferenceRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/integrations", tags=["Integrations & Plugins"])


@router.post(
    "/slack/slash",
    status_code=status.HTTP_200_OK,
)
async def handle_slack_slash_command(
    request: Request,
    background_tasks: BackgroundTasks,
    x_slack_signature: str | None = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str | None = Header(None, alias="X-Slack-Request-Timestamp"),
) -> dict[str, Any]:
    """Handle incoming Slack slash command (e.g. `/ask-retriever <query>`)."""
    raw_body = await request.body()

    # 1. Verify cryptographic Slack signature if secret is configured
    slack_secret = getattr(settings, "SLACK_SIGNING_SECRET", None) or os.environ.get("SLACK_SIGNING_SECRET")
    if slack_secret:
        is_valid = slack_service.verify_slack_signature(
            signing_secret=slack_secret,
            timestamp=x_slack_request_timestamp,
            signature=x_slack_signature,
            raw_body=raw_body,
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Slack request signature.",
            )

    # 2. Parse form body (Slack transmits application/x-www-form-urlencoded)
    try:
        form_data = await request.form()
        query_text = form_data.get("text", "").strip()
        user_name = form_data.get("user_name", "Slack User")
        channel_id = form_data.get("channel_id", "default")
        team_id = form_data.get("team_id", "default_team")
    except Exception:
        # Fallback to JSON payload if tested via direct REST
        try:
            json_data = await request.json()
            query_text = json_data.get("text", "").strip()
            user_name = json_data.get("user_name", "User")
            channel_id = json_data.get("channel_id", "default")
            team_id = json_data.get("team_id", "default_team")
        except Exception:
            query_text = ""
            user_name = "User"
            channel_id = "default"
            team_id = "default_team"

    if not query_text:
        return {
            "response_type": "ephemeral",
            "text": "👋 *Retriever AI Assistant*\nUsage: `/ask-retriever <your question>`\nExample: `/ask-retriever What is our engineering deployment checklist?`",
        }

    logger.info(
        "Processing Slack slash command from user '%s' in channel '%s' (team '%s')",
        user_name,
        channel_id,
        team_id,
    )

    # Resolve target tenant (default to prateeq_scoping or channel mapped tenant)
    tenant_id = os.environ.get("SLACK_DEFAULT_TENANT_ID", "prateeq_scoping")
    start_time = time.time()

    # 3. Retrieve relevant context chunks
    citations: list[dict[str, Any]] = []
    context_blocks: list[str] = []

    try:
        search_results = await search_service.search_hybrid(
            tenant_id=tenant_id,
            query=query_text,
            limit=4,
        )
        for res in search_results:
            snippet = res.content[:300].strip()
            context_blocks.append(f"[{res.document_id}]: {snippet}")
            citations.append(
                {
                    "title": res.metadata.get("filename") or f"Doc {res.document_id[:8]}",
                    "snippet": snippet,
                    "url": f"https://prateeq.in/rag/app?tenant={tenant_id}",
                    "score": res.score,
                }
            )
    except Exception as exc:
        logger.warning("Slack search lookup failed for tenant %s: %s", tenant_id, exc)

    # 4. Generate grounded completion
    system_prompt = (
        "You are Retriever AI, an enterprise knowledge copilot for Slack. "
        "Answer the user's question concisely, professionally, and ground your response strictly in the provided document context. "
        "If the answer cannot be found in the context, explicitly state so."
    )
    user_prompt = f"Context:\n{chr(10).join(context_blocks)}\n\nQuestion: {query_text}"

    try:
        inference_req = InferenceRequest(
            tenant_id=tenant_id,
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ],
            stream=False,
        )
        inference_res = await inference_orchestrator.chat(inference_req)
        answer_text = inference_res.content
    except Exception as exc:
        logger.warning("Slack inference failed: %s", exc)
        if context_blocks:
            answer_text = "Found relevant context chunks:\n\n" + "\n\n".join(context_blocks[:2])
        else:
            answer_text = "I searched the workspace knowledge base but found no relevant documents matching your query."

    duration_ms = (time.time() - start_time) * 1000.0

    # 5. Build and return Slack Block Kit message
    return slack_service.build_slack_block_response(
        query=query_text,
        answer=answer_text,
        citations=citations,
        tenant_id=tenant_id,
        duration_ms=duration_ms,
    )


@router.post(
    "/slack/events",
    status_code=status.HTTP_200_OK,
)
async def handle_slack_events(request: Request) -> dict[str, Any]:
    """Handle Slack event subscription handshakes and webhooks."""
    payload = await request.json()

    # Handle Slack URL verification challenge
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge")}

    # Process other asynchronous Slack events
    event_type = payload.get("event", {}).get("type", "unknown")
    logger.info("Received Slack event: %s", event_type)
    return {"status": "accepted", "event_type": event_type}


@router.get(
    "/extension/bundle",
    status_code=status.HTTP_200_OK,
)
async def download_chrome_extension_bundle() -> Response:
    """Dynamically package and serve the 1-Click Chrome Ingestion Extension as a ZIP bundle."""
    # Find extension directory relative to API root
    current_dir = Path(__file__).resolve().parent
    # Navigate up from src/routers to apps/extension
    extension_dir = current_dir.parent.parent.parent / "extension"

    if not extension_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chrome extension source directory not found.",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in extension_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                archive_name = file_path.relative_to(extension_dir)
                zip_file.write(file_path, arcname=str(archive_name))

    zip_buffer.seek(0)
    zip_bytes = zip_buffer.getvalue()

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=retriever-chrome-extension.zip",
            "Content-Length": str(len(zip_bytes)),
        },
    )


@router.get(
    "/overview",
    status_code=status.HTTP_200_OK,
)
async def get_integrations_overview() -> dict[str, Any]:
    """Return overview of all available ecosystem plugins and connection states."""
    slack_configured = bool(getattr(settings, "SLACK_SIGNING_SECRET", None) or os.environ.get("SLACK_SIGNING_SECRET"))

    return {
        "plugins": [
            {
                "id": "slack",
                "name": "Slack Workspace Bot",
                "category": "Messaging",
                "status": "configured" if slack_configured else "available",
                "slash_command": "/ask-retriever",
                "webhook_url": "https://rag.prateeq.in/v1/integrations/slack/slash",
                "description": "Ask questions and get cited answers directly inside team Slack channels.",
            },
            {
                "id": "chrome_extension",
                "name": "1-Click Chrome Extension",
                "category": "Browser",
                "status": "available",
                "download_url": "/v1/integrations/extension/bundle",
                "description": "One-click ingestion of articles, PDFs, and web pages into your tenant knowledge base.",
            },
            {
                "id": "google_drive",
                "name": "Google Drive 2-Way Sync",
                "category": "Cloud Storage",
                "status": "available",
                "description": "Continuous sync of target Google Drive folders with differential vector indexing.",
            },
            {
                "id": "notion",
                "name": "Notion Knowledge Base",
                "category": "Documentation",
                "status": "available",
                "description": "Sync Notion databases and page block trees directly into your vector store.",
            },
        ]
    }
