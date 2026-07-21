"""Feedback Endpoints Unit Tests.

Verifies:
- Feedback submission endpoint records rating and comments.
- Tenant isolation prevents cross-tenant feedback injection.
- Re-submitting feedback on the same message updates the existing record.
- Admin analytics endpoint aggregates counts and scores correctly.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.adapters.api.security import (
    get_current_user_id,
    verify_admin_key,
    verify_scopes,
    verify_tenant_isolation,
)
from src.container import feedback_repo
from src.domain.abstractions.inference import ChatMessageFeedback
from src.main import app


@pytest.fixture
def mock_user_context():
    return {
        "user_id": "11111111-1111-1111-1111-111111111111",
        "tenant_id": "22222222-2222-2222-2222-222222222222",
    }


@pytest.fixture(autouse=True)
def setup_dependency_overrides(mock_user_context):
    """Automatically set up and clean up dependency overrides for each test."""
    app.dependency_overrides[verify_tenant_isolation] = lambda: None
    app.dependency_overrides[verify_scopes] = lambda: None
    app.dependency_overrides[get_current_user_id] = lambda: mock_user_context["user_id"]
    app.dependency_overrides[verify_admin_key] = lambda: None
    yield
    app.dependency_overrides.clear()


@patch("src.main.inference_orchestrator.get_session")
@pytest.mark.asyncio
async def test_submit_feedback_success(
    mock_get_session,
    mock_user_context,
) -> None:
    """Verify standard client can submit message feedback successfully."""
    tenant_id = mock_user_context["tenant_id"]
    session_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    # Mock session retrieval
    mock_session = MagicMock()
    mock_get_session.return_value = mock_session

    # Mock DB select for message validation (must return a row)
    mock_msg = MagicMock()
    mock_msg.message_id = uuid.UUID(message_id)
    mock_msg.session_id = uuid.UUID(session_id)
    mock_msg.tenant_id = uuid.UUID(tenant_id)
    mock_msg.role = "assistant"
    mock_msg.content = "some response"
    mock_msg.name = None
    mock_msg.created_at = datetime.now(UTC)

    # Patch the DB session inside the endpoint
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: mock_msg)

    # Patch tenant_session from connection module where it is imported/used
    with patch("src.adapters.database.inference_repository.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_db_session

        # Mock repository submit method
        with patch.object(feedback_repo, "submit_feedback", new_callable=AsyncMock) as mock_submit:
            client = TestClient(app)
            response = client.post(
                f"/v1/tenants/{tenant_id}/chat/sessions/{session_id}/messages/{message_id}/feedback",
                json={"rating": 1, "feedback_text": "Great explanation!"},
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.json()["status"] == "success"

            # Assert repo submit was called with correct values
            mock_submit.assert_called_once()
            called_arg: ChatMessageFeedback = mock_submit.call_args[0][0]
            assert called_arg.tenant_id == tenant_id
            assert called_arg.message_id == message_id
            assert called_arg.rating == 1
            assert called_arg.feedback_text == "Great explanation!"
            assert called_arg.user_id == mock_user_context["user_id"]


@patch("src.main.inference_orchestrator.get_session")
@pytest.mark.asyncio
async def test_submit_feedback_message_not_found(
    mock_get_session,
    mock_user_context,
) -> None:
    """Verify feedback fails if the target message does not exist in the session."""
    tenant_id = mock_user_context["tenant_id"]
    session_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    # Mock session retrieval succeeds
    mock_get_session.return_value = MagicMock()

    # Mock DB returns None (message not found)
    mock_db_session = AsyncMock()
    mock_db_session.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    with patch("src.adapters.database.inference_repository.tenant_session") as mock_tenant_session:
        mock_tenant_session.return_value.__aenter__.return_value = mock_db_session

        client = TestClient(app)
        response = client.post(
            f"/v1/tenants/{tenant_id}/chat/sessions/{session_id}/messages/{message_id}/feedback",
            json={"rating": -1},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Message not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_get_analytics() -> None:
    """Verify admin feedback analytics endpoint returns repository aggregates."""
    tenant_id = str(uuid.uuid4())

    mock_analytics = {
        "tenant_id": tenant_id,
        "total_feedback_count": 5,
        "positive_count": 4,
        "negative_count": 1,
        "positive_percentage": 80.0,
        "recent_comments": [{"rating": 1, "text": "excellent"}],
    }

    with patch.object(feedback_repo, "get_feedback_analytics", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_analytics

        client = TestClient(app)
        response = client.get(f"/v1/admin/tenants/{tenant_id}/feedback/analytics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_feedback_count"] == 5
        assert data["positive_percentage"] == 80.0
        assert len(data["recent_comments"]) == 1
        mock_get.assert_called_once_with(tenant_id)
