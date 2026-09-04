"""Unit and integration tests for Milestone 90 Universal Ecosystem Plugins."""
import hashlib
import hmac
import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from src.domain.abstractions.connector import ConnectorConfig
from src.domain.connectors.google_drive import GoogleDriveConnector
from src.domain.connectors.notion import NotionConnector
from src.domain.connectors.registry import ConnectorRegistry
from src.domain.integrations.slack_service import SlackService
from src.main import app


def test_slack_signature_verification():
    """Verify Slack HMAC-SHA256 signature verification logic and replay attack guard."""
    secret = "test_slack_signing_secret_12345"
    current_time = str(int(time.time()))
    body = b"command=%2Fask-retriever&text=test+query"

    # Compute authentic signature
    sig_basestring = f"v0:{current_time}:{body.decode('utf-8')}".encode()
    computed_hash = hmac.new(secret.encode("utf-8"), sig_basestring, hashlib.sha256).hexdigest()
    valid_sig = f"v0={computed_hash}"

    # 1. Authentic request should pass
    assert SlackService.verify_slack_signature(secret, current_time, valid_sig, body) is True

    # 2. Tampered signature should fail
    tampered_sig = "v0=invalid_signature_hash_0000000000000"
    assert SlackService.verify_slack_signature(secret, current_time, tampered_sig, body) is False

    # 3. Expired request (>300s old) should fail
    expired_time = str(int(time.time()) - 600)
    assert SlackService.verify_slack_signature(secret, expired_time, valid_sig, body) is False

    # 4. Missing parameters should fail
    assert SlackService.verify_slack_signature("", current_time, valid_sig, body) is False
    assert SlackService.verify_slack_signature(secret, None, valid_sig, body) is False


def test_slack_block_kit_response_composition():
    """Verify Slack Block Kit interactive message construction."""
    query = "What is our deployment policy?"
    answer = "All production releases require CI/CD passing tests and code review."
    citations = [
        {"title": "Deployment SOP", "url": "https://wiki.corp/deploy", "score": 0.95},
        {"title": "Security Guidelines", "url": "https://wiki.corp/security", "score": 0.88},
    ]

    response = SlackService.build_slack_block_response(
        query=query,
        answer=answer,
        citations=citations,
        tenant_id="tn_test_enterprise",
        duration_ms=142.5,
    )

    assert response["response_type"] == "in_channel"
    assert "blocks" in response
    blocks = response["blocks"]

    # Must contain section, citations, context, and actions
    block_types = [b["type"] for b in blocks]
    assert "section" in block_types
    assert "context" in block_types
    assert "actions" in block_types

    # Verify buttons inside action block
    action_block = next(b for b in blocks if b["type"] == "actions")
    buttons = action_block["elements"]
    button_action_ids = [btn["action_id"] for btn in buttons]
    assert "btn_feedback_pos" in button_action_ids
    assert "btn_feedback_neg" in button_action_ids
    assert "btn_open_studio" in button_action_ids


@pytest.mark.asyncio
async def test_google_drive_connector_discovery():
    """Verify Google Drive connector credential probe and document discovery in sandbox mode."""
    connector = GoogleDriveConnector()

    config = ConnectorConfig(
        id="conn_gdrive_1",
        name="Engineering Docs GDrive",
        connector_type="google_drive",
        configuration={
            "folder_id": "1A2B3C4D5E6F",
            "offline_sandbox": True,
        },
    )

    is_valid = await connector.validate_credentials(config)
    assert is_valid is True

    docs = await connector.fetch_documents(config)
    assert len(docs) >= 1
    assert "gdrive" in docs[0].filename
    assert docs[0].metadata["source"] == "google_drive"
    assert docs[0].metadata["folder_id"] == "1A2B3C4D5E6F"


@pytest.mark.asyncio
async def test_notion_connector_markdown_parsing():
    """Verify Notion connector block parsing converts headings, paragraphs, and lists to markdown."""
    connector = NotionConnector()

    sample_blocks = [
        {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Architecture Overview"}]}},
        {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "This is our primary stack."}]}},
        {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": [{"plain_text": "FastAPI"}]}},
        {"type": "code", "code": {"language": "python", "rich_text": [{"plain_text": "print('hello')"}]}},
    ]

    md_output = "".join([connector._parse_block_to_markdown(b) for b in sample_blocks])
    assert "# Architecture Overview" in md_output
    assert "This is our primary stack." in md_output
    assert "- FastAPI" in md_output
    assert "```python\nprint('hello')\n```" in md_output

    # Test sandbox fetch
    config = ConnectorConfig(
        id="conn_notion_1",
        name="Team Wiki",
        connector_type="notion",
        configuration={"database_id": "db_wiki_999", "offline_sandbox": True},
    )
    docs = await connector.fetch_documents(config)
    assert len(docs) >= 1
    assert docs[0].metadata["source"] == "notion"


def test_connector_registry_resolution():
    """Verify that ConnectorRegistry returns real instances instead of mocks."""
    gdrive_conn = ConnectorRegistry.get_connector("google_drive")
    assert isinstance(gdrive_conn, GoogleDriveConnector)

    notion_conn = ConnectorRegistry.get_connector("notion")
    assert isinstance(notion_conn, NotionConnector)


def test_chrome_extension_bundle_download():
    """Verify that GET /v1/integrations/extension/bundle returns a valid zip containing manifest.json."""
    client = TestClient(app)
    response = client.get("/v1/integrations/extension/bundle")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "retriever-chrome-extension.zip" in response.headers["content-disposition"]

    # Verify zip archive contents
    zip_bytes = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_bytes, "r") as z:
        namelist = z.namelist()
        assert "manifest.json" in namelist
        assert "popup.html" in namelist
        assert "popup.js" in namelist


def test_hexagonal_architecture_integrations():
    """Ensure integration and connector domain files never import FastAPI or database engines."""
    import inspect

    import src.domain.connectors.google_drive as gd_mod
    import src.domain.connectors.notion as nt_mod
    import src.domain.integrations.slack_service as sl_mod

    for mod in (gd_mod, nt_mod, sl_mod):
        source = inspect.getsource(mod)
        assert "from fastapi" not in source, f"{mod.__name__} violates Hexagonal boundary by importing FastAPI"
        assert "from sqlalchemy" not in source, f"{mod.__name__} violates Hexagonal boundary by importing SQLAlchemy"
        assert "from src.routers" not in source, f"{mod.__name__} violates Hexagonal boundary by importing routers"
