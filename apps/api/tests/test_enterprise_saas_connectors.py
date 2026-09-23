"""Automated test suite for Turn-Key Enterprise SaaS Connectors (Milestone 125)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.abstractions.connector import (
    ConnectorConfig,
    ConnectorSyncState,
)
from src.domain.connectors.confluence_jira import (
    ConfluenceConnector,
    JiraConnector,
    _html_to_markdown,
)
from src.domain.connectors.google_drive import GoogleDriveConnector
from src.domain.connectors.microsoft365 import Microsoft365Connector
from src.domain.connectors.notion import NotionConnector
from src.domain.connectors.registry import ConnectorRegistry

# ==============================================================================
# Google Drive & Docs Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_google_drive_manifest_and_validation():
    connector = GoogleDriveConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "google_drive"
    assert manifest.supports_incremental is True
    assert "folder_id" in manifest.required_parameters

    # Sandbox credential validation
    config_sandbox = ConnectorConfig(
        id="conn_gdrive_1",
        name="Corp Drive",
        connector_type="google_drive",
        configuration={"folder_id": "root_123", "offline_sandbox": True},
    )
    assert await connector.validate_credentials(config_sandbox) is True

    # Missing folder_id
    config_invalid = ConnectorConfig(
        id="conn_gdrive_2",
        name="Corp Drive",
        connector_type="google_drive",
        configuration={"access_token": "token_xyz"},
    )
    assert await connector.validate_credentials(config_invalid) is False


def test_google_drive_acl_parsing():
    # Anyone access -> is_public = True
    perms_public = [{"type": "anyone", "role": "reader"}]
    u, g, is_pub = GoogleDriveConnector._parse_permissions(perms_public)
    assert is_pub is True
    assert u == []

    # Restricted access with specific user and group
    perms_restricted = [
        {"type": "user", "role": "reader", "emailAddress": "alice@corp.internal"},
        {"type": "group", "role": "writer", "emailAddress": "security-team@corp.internal"},
        {"type": "domain", "role": "reader", "domain": "corp.internal"},
    ]
    u, g, is_pub = GoogleDriveConnector._parse_permissions(perms_restricted)
    assert is_pub is False
    assert "alice@corp.internal" in u
    assert "security-team@corp.internal" in g
    assert "corp.internal" in g


@pytest.mark.asyncio
async def test_google_drive_sandbox_and_incremental():
    connector = GoogleDriveConnector()
    config = ConnectorConfig(
        id="conn_gdrive_test",
        name="Google Drive Sandbox",
        connector_type="google_drive",
        configuration={"folder_id": "folder_abc", "offline_sandbox": True},
    )

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert any(d.is_public is True for d in docs)
    assert any(d.is_public is False and "security-team" in d.allowed_groups for d in docs)

    state = ConnectorSyncState()
    inc_docs, new_state = await connector.fetch_incremental(config, state)
    assert len(inc_docs) == 2
    assert new_state.cursor is not None


# ==============================================================================
# Notion Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_notion_manifest_and_table_parsing():
    connector = NotionConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "notion"
    assert manifest.supports_incremental is True
    assert "database_id" in manifest.required_parameters

    # Table formatting test
    table_data = {"table_width": 2, "has_column_header": True}
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "results": [
            {
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"plain_text": "Feature"}],
                        [{"plain_text": "Status"}],
                    ]
                },
            },
            {
                "type": "table_row",
                "table_row": {
                    "cells": [
                        [{"plain_text": "Vector Search"}],
                        [{"plain_text": "Production"}],
                    ]
                },
            },
        ]
    }

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_res)

    md_table = await connector._fetch_table_markdown(
        client=mock_client,
        table_block_id="tbl_123",
        headers={},
        table_data=table_data,
    )
    assert "| Feature | Status |" in md_table
    assert "| Vector Search | Production |" in md_table


@pytest.mark.asyncio
async def test_notion_sandbox_and_incremental():
    connector = NotionConnector()
    config = ConnectorConfig(
        id="conn_notion_test",
        name="Notion Sandbox",
        connector_type="notion",
        configuration={"database_id": "db_notion_xyz", "offline_sandbox": True},
    )

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert any("| Vector Engine |" in d.content for d in docs)
    assert any("engineering" in d.allowed_groups for d in docs)

    state = ConnectorSyncState(cursor="2026-09-01T00:00:00Z")
    inc_docs, new_state = await connector.fetch_incremental(config, state)
    assert len(inc_docs) >= 1
    assert new_state.cursor is not None


# ==============================================================================
# Atlassian Confluence Tests
# ==============================================================================


def test_confluence_html_macro_conversion():
    raw_xhtml = (
        '<h1>Sprint Goals</h1>'
        '<ac:structured-macro ac:name="info">'
        '<ac:rich-text-body>Remember to tag reviewers.</ac:rich-text-body>'
        '</ac:structured-macro>'
        '<p>Please check <strong>architecture</strong> guidelines.</p>'
        '<table><tr><th>Component</th><th>Owner</th></tr><tr><td>Vector Rerank</td><td>Search Team</td></tr></table>'
        '<ac:structured-macro ac:name="code">'
        '<ac:plain-text-body><![CDATA[def search(): pass]]></ac:plain-text-body>'
        '</ac:structured-macro>'
    )
    md = _html_to_markdown(raw_xhtml)
    assert "# Sprint Goals" in md
    assert "> [!NOTE]" in md
    assert "Remember to tag reviewers." in md
    assert "**architecture**" in md
    assert "| Component | Owner |" in md
    assert "| Vector Rerank | Search Team |" in md
    assert "```\ndef search(): pass\n```" in md


@pytest.mark.asyncio
async def test_confluence_connector_sandbox_and_manifest():
    connector = ConfluenceConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "confluence"
    assert manifest.supports_incremental is True
    assert "space_key" in manifest.required_parameters

    config = ConnectorConfig(
        id="conn_confluence_test",
        name="Confluence Knowledge",
        connector_type="confluence",
        configuration={"space_key": "ENG", "offline_sandbox": True},
    )
    assert await connector.validate_credentials(config) is True

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert any("Microservices Architecture Blueprint" in d.content for d in docs)
    assert any("ciso@company.com" in d.allowed_users for d in docs)

    state = ConnectorSyncState()
    inc_docs, new_state = await connector.fetch_incremental(config, state)
    assert len(inc_docs) == 2
    assert new_state.cursor is not None


# ==============================================================================
# Atlassian Jira Software Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_jira_connector_sandbox_and_formatting():
    connector = JiraConnector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "jira"
    assert manifest.supports_incremental is True
    assert "project_key" in manifest.required_parameters

    config = ConnectorConfig(
        id="conn_jira_test",
        name="Jira Board",
        connector_type="jira",
        configuration={"project_key": "PROJ", "offline_sandbox": True},
    )
    assert await connector.validate_credentials(config) is True

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert any("[PROJ-101]" in d.content for d in docs)
    assert any("alice@corp.internal" in d.allowed_users for d in docs)
    assert any("jira-developers-proj" in d.allowed_groups for d in docs)

    # Test issue formatting helper directly
    mock_issue = {
        "key": "DEV-42",
        "fields": {
            "summary": "Fix connection pooling latency",
            "status": {"name": "In Progress"},
            "issuetype": {"name": "Bug"},
            "priority": {"name": "High"},
            "assignee": {"emailAddress": "dev@corp.internal", "displayName": "Dev User"},
            "reporter": {"emailAddress": "qa@corp.internal", "displayName": "QA User"},
            "created": "2026-09-20",
            "updated": "2026-09-22",
            "description": "Connection exhaustion observed on replica 3.",
            "project": {"key": "DEV"},
            "security": {"name": "Confidential Security"},
            "comment": {
                "comments": [
                    {
                        "author": {"displayName": "Dev User"},
                        "created": "2026-09-21",
                        "body": "Pushed pool size bump to 50.",
                    }
                ]
            },
        },
    }
    md, users, groups, is_pub = JiraConnector._format_issue_markdown(mock_issue, "https://jira.corp.internal")
    assert "[DEV-42] Fix connection pooling latency" in md
    assert "dev@corp.internal" in users
    assert "qa@corp.internal" in users
    assert "jira-project-dev" in groups
    assert "jira-security-confidential-security" in groups
    assert is_pub is False


# ==============================================================================
# Microsoft 365 (SharePoint & OneDrive) Tests
# ==============================================================================


def test_microsoft_graph_acl_parsing():
    # Anonymous link -> is_public = True
    perms_link = [{"link": {"scope": "anonymous"}}]
    u, g, is_pub = Microsoft365Connector._parse_graph_permissions(perms_link)
    assert is_pub is True

    # Granted identities with Azure AD users and groups
    perms_identities = [
        {
            "grantedToV2": {
                "user": {"userPrincipalName": "executive@enterprise.onmicrosoft.com"},
                "group": {"displayName": "Board-Auditors"},
            }
        },
        {
            "grantedToIdentitiesV2": [
                {"group": {"displayName": "Security-Admins"}},
                {"user": {"email": "analyst@enterprise.onmicrosoft.com"}},
            ]
        },
        {"link": {"scope": "organization"}},
    ]
    u, g, is_pub = Microsoft365Connector._parse_graph_permissions(perms_identities)
    assert is_pub is False
    assert "executive@enterprise.onmicrosoft.com" in u
    assert "analyst@enterprise.onmicrosoft.com" in u
    assert "Board-Auditors" in g
    assert "Security-Admins" in g
    assert "organization-members" in g


@pytest.mark.asyncio
async def test_microsoft365_sandbox_and_manifest():
    connector = Microsoft365Connector()
    manifest = connector.get_manifest()
    assert manifest.connector_type == "microsoft365"
    assert manifest.supports_incremental is True
    assert "drive_id" in manifest.required_parameters

    config = ConnectorConfig(
        id="conn_m365_test",
        name="SharePoint Corp Library",
        connector_type="microsoft365",
        configuration={"drive_id": "drive_root_001", "offline_sandbox": True},
    )
    assert await connector.validate_credentials(config) is True

    docs = await connector.fetch_documents(config)
    assert len(docs) == 2
    assert any("Enterprise Cloud Governance Policy" in d.content for d in docs)
    assert any("organization-members" in d.allowed_groups for d in docs)
    assert any("executive-leadership" in d.allowed_groups for d in docs)

    state = ConnectorSyncState()
    inc_docs, new_state = await connector.fetch_incremental(config, state)
    assert len(inc_docs) == 2
    assert new_state.cursor == "delta_link_sandbox_completed"


# ==============================================================================
# Connector Registry Catalog Tests
# ==============================================================================


def test_connector_registry_catalog():
    manifests = ConnectorRegistry.list_manifests()
    types = {m.connector_type for m in manifests}

    assert "google_drive" in types
    assert "notion" in types
    assert "confluence" in types
    assert "jira" in types
    assert "microsoft365" in types

    # Check resolution
    assert isinstance(ConnectorRegistry.get_connector("confluence"), ConfluenceConnector)
    assert isinstance(ConnectorRegistry.get_connector("jira"), JiraConnector)
    assert isinstance(ConnectorRegistry.get_connector("microsoft365"), Microsoft365Connector)
    assert isinstance(ConnectorRegistry.get_connector("sharepoint"), Microsoft365Connector)
    assert isinstance(ConnectorRegistry.get_connector("google_drive"), GoogleDriveConnector)
    assert isinstance(ConnectorRegistry.get_connector("notion"), NotionConnector)


def test_hexagonal_architecture_enterprise_connectors():
    """Ensure connector domain implementations have zero forbidden framework or adapter imports."""
    import ast
    import os

    target_files = [
        "apps/api/src/domain/connectors/google_drive.py",
        "apps/api/src/domain/connectors/notion.py",
        "apps/api/src/domain/connectors/confluence_jira.py",
        "apps/api/src/domain/connectors/microsoft365.py",
    ]

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    forbidden_prefixes = ("src.adapters", "src.routers", "sqlalchemy", "fastapi")

    for rel_path in target_files:
        full_path = os.path.join(base_dir, rel_path)
        with open(full_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=full_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"Forbidden import '{alias.name}' in {rel_path}"
                        )
            elif isinstance(node, ast.ImportFrom) and node.module:
                for forbidden in forbidden_prefixes:
                    assert not node.module.startswith(forbidden), (
                        f"Forbidden import '{node.module}' in {rel_path}"
                    )
