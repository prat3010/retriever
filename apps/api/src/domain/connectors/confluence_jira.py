"""Authentic Atlassian Confluence Cloud & Jira Software REST API Connectors."""
import base64
import html
import logging
import re
from typing import Any

import httpx

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
    DiscoveredDocument,
)

logger = logging.getLogger(__name__)


def _html_to_markdown(raw_html: str) -> str:
    """Convert Confluence XHTML storage format or Jira rendered HTML to standard Markdown."""
    if not raw_html:
        return ""

    text = raw_html

    # Replace Confluence code macros: <ac:structured-macro ac:name="code">...<ac:plain-text-body><![CDATA[...]]></ac:plain-text-body></ac:structured-macro>
    code_pattern = re.compile(
        r'<ac:structured-macro[^>]*ac:name="code"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?</ac:structured-macro>',
        re.DOTALL | re.IGNORECASE,
    )
    text = code_pattern.sub(r"\n```\n\1\n```\n", text)

    # Replace Confluence callout macros (info, note, tip, warning)
    macro_callouts = {
        "info": "[!NOTE]",
        "tip": "[!TIP]",
        "note": "[!NOTE]",
        "warning": "[!WARNING]",
    }
    for m_name, alert_tag in macro_callouts.items():
        pattern = re.compile(
            rf'<ac:structured-macro[^>]*ac:name="{m_name}"[^>]*>.*?<ac:rich-text-body>(.*?)</ac:rich-text-body>.*?</ac:structured-macro>',
            re.DOTALL | re.IGNORECASE,
        )
        text = pattern.sub(rf"\n> {alert_tag}\n> \1\n", text)

    # Strip remaining XML/AC namespaces tags
    text = re.sub(r"</?ac:[^>]+>", "", text)
    text = re.sub(r"</?ri:[^>]+>", "", text)

    # Convert HTML Headings
    for h in range(1, 7):
        text = re.sub(
            rf"<h{h}[^>]*>(.*?)</h{h}>",
            rf"\n{'#' * h} \1\n\n",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

    # Convert Bold and Italic
    text = re.sub(r"<(?:strong|b)>(.*?)</(?:strong|b)>", r"**\1**", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(?:em|i)>(.*?)</(?:em|i)>", r"*\1*", text, flags=re.IGNORECASE | re.DOTALL)

    # Convert links <a href="...">...</a>
    text = re.sub(
        r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        r"[\2](\1)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Convert Lists
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"</?[ou]l[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Convert Paragraphs & Line Breaks
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Convert Tables: <table><tr><th>/<td>
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.DOTALL | re.IGNORECASE)

    def _replace_table(match: re.Match) -> str:
        table_html = match.group(1)
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
        if not rows:
            return ""

        parsed_rows: list[list[str]] = []
        is_first_header = False

        for row_html in rows:
            headers = re.findall(r"<th[^>]*>(.*?)</th>", row_html, re.DOTALL | re.IGNORECASE)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.DOTALL | re.IGNORECASE)
            if headers:
                is_first_header = True
                parsed_rows.append([re.sub(r"<[^>]+>", "", h).strip() for h in headers])
            elif cells:
                parsed_rows.append([re.sub(r"<[^>]+>", "", c).strip() for c in cells])

        if not parsed_rows:
            return ""

        col_count = max(len(r) for r in parsed_rows)
        # Pad shorter rows
        for r in parsed_rows:
            if len(r) < col_count:
                r.extend([""] * (col_count - len(r)))

        out_lines: list[str] = []
        if is_first_header:
            out_lines.append("| " + " | ".join(parsed_rows[0]) + " |")
            out_lines.append("| " + " | ".join(["---"] * col_count) + " |")
            for r in parsed_rows[1:]:
                out_lines.append("| " + " | ".join(r) + " |")
        else:
            default_hd = [f"Column {i+1}" for i in range(col_count)]
            out_lines.append("| " + " | ".join(default_hd) + " |")
            out_lines.append("| " + " | ".join(["---"] * col_count) + " |")
            for r in parsed_rows:
                out_lines.append("| " + " | ".join(r) + " |")

        return "\n" + "\n".join(out_lines) + "\n\n"

    text = table_pattern.sub(_replace_table, text)

    # Strip any residual HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Normalize multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class ConfluenceConnector(BaseConnector):
    """Production-grade Atlassian Confluence Cloud Connector.

    Supports:
    - Basic auth (email + API token) or OAuth bearer token.
    - Querying spaces and pages via CQL.
    - XHTML storage format to Markdown conversion (code macros, callouts, tables).
    - Page restriction ACL extraction (read restriction users & groups).
    - Incremental differential change sync via lastModified timestamp.
    """

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="confluence",
            name="Atlassian Confluence Cloud",
            description="Extracts spaces, documentation hierarchies, and restricted pages with ACL preservation.",
            icon="book-open",
            supports_incremental=True,
            required_parameters=["cloud_url", "email", "api_token", "space_key"],
            optional_parameters={"expand_macros": True, "cql": ""},
        )

    def _get_headers(self, config: ConnectorConfig) -> dict[str, str]:
        email = config.configuration.get("email", "")
        api_token = config.configuration.get("api_token", "")
        access_token = config.configuration.get("access_token", "")

        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        elif email and api_token:
            basic = base64.b64encode(f"{email}:{api_token}".encode()).decode("utf-8")
            headers["Authorization"] = f"Basic {basic}"
        return headers

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        space_key = config.configuration.get("space_key")
        if not space_key:
            return False

        if config.configuration.get("offline_sandbox", False):
            return True

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        headers = self._get_headers(config)
        if not cloud_url or not headers.get("Authorization"):
            return False

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{cloud_url}/wiki/rest/api/space/{space_key}", headers=headers)
                return res.status_code in (200, 404)
        except Exception as exc:
            logger.warning("Confluence credential validation error: %s", exc)
            return False

    def _get_sandbox_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        space_key = config.configuration.get("space_key", "ENG")
        cloud_url = config.configuration.get("cloud_url", "https://enterprise.atlassian.net").rstrip("/")
        return [
            DiscoveredDocument(
                filename="confluence_architecture_blueprint.md",
                content=(
                    f"# [{space_key}] Microservices Architecture Blueprint\n\n"
                    "High-level system topology and inter-service communications.\n\n"
                    "> [!NOTE]\n> All external API gateways require mutual TLS and HMAC request validation.\n\n"
                    "| Service | Tech Stack | Ownership Team |\n"
                    "| --- | --- | --- |\n"
                    "| API Gateway | FastAPI / Rust | Core Infra |\n"
                    "| Vector Engine | PostgreSQL / pgvector | Search & Intelligence |\n"
                    "| Event Bus | Apache Kafka | Data Platform |\n"
                ),
                mime_type="text/markdown",
                source_url=f"{cloud_url}/wiki/spaces/{space_key}/pages/10001",
                allowed_users=[],
                allowed_groups=["confluence-users", "engineering-org"],
                is_public=False,
                metadata={
                    "connector_id": config.id,
                    "source": "confluence",
                    "space_key": space_key,
                    "page_id": "10001",
                    "sync_mode": "sandbox",
                },
            ),
            DiscoveredDocument(
                filename="confluence_security_compliance_policy.md",
                content=(
                    f"# [{space_key}] Security Compliance & Secret Hygiene\n\n"
                    "Mandatory guidelines for secret rotation and cryptographic key access.\n"
                    "Accessible only by designated Security Council members."
                ),
                mime_type="text/markdown",
                source_url=f"{cloud_url}/wiki/spaces/{space_key}/pages/10002",
                allowed_users=["ciso@company.com", "security-lead@company.com"],
                allowed_groups=["security-auditors"],
                is_public=False,
                metadata={
                    "connector_id": config.id,
                    "source": "confluence",
                    "space_key": space_key,
                    "page_id": "10002",
                    "sync_mode": "sandbox",
                },
            ),
        ]

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        space_key = config.configuration.get("space_key", "")
        if not space_key:
            logger.warning("Confluence connector '%s' missing space_key", config.id)
            return []

        if config.configuration.get("offline_sandbox", False):
            return self._get_sandbox_documents(config)

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        if not cloud_url:
            logger.warning("Confluence connector '%s' missing cloud_url", config.id)
            return []

        headers = self._get_headers(config)
        if not headers.get("Authorization"):
            logger.error("Confluence connector '%s' missing credentials", config.id)
            return []

        discovered: list[DiscoveredDocument] = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = (
                    f"{cloud_url}/wiki/rest/api/content"
                    f"?type=page&spaceKey={space_key}"
                    f"&expand=body.storage,version,restrictions.read.restrictions.user,restrictions.read.restrictions.group"
                    f"&limit=50"
                )
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    logger.error("Confluence API returned HTTP %d: %s", res.status_code, res.text[:200])
                    return []

                pages = res.json().get("results", [])
                for page in pages:
                    page_id = page.get("id", "")
                    title = page.get("title", f"confluence_page_{page_id}")
                    version_info = page.get("version", {})
                    when = version_info.get("when", "")

                    raw_body = page.get("body", {}).get("storage", {}).get("value", "")
                    markdown_content = _html_to_markdown(raw_body)
                    if not markdown_content:
                        markdown_content = f"# {title}\n\n*Empty Confluence page.*"

                    # ACL restrictions parsing
                    allowed_users: list[str] = []
                    allowed_groups: list[str] = []
                    is_public = True

                    read_restrictions = page.get("restrictions", {}).get("read", {}).get("restrictions", {})
                    user_restrictions = read_restrictions.get("user", {}).get("results", [])
                    group_restrictions = read_restrictions.get("group", {}).get("results", [])

                    for u in user_restrictions:
                        u_id = u.get("email") or u.get("accountId") or u.get("username")
                        if u_id:
                            allowed_users.append(u_id)

                    for g in group_restrictions:
                        g_name = g.get("name")
                        if g_name:
                            allowed_groups.append(g_name)

                    if allowed_users or allowed_groups:
                        is_public = False

                    filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', title).lower()}_{page_id}.md"
                    web_url = f"{cloud_url}/wiki/spaces/{space_key}/pages/{page_id}"

                    discovered.append(
                        DiscoveredDocument(
                            filename=filename,
                            content=markdown_content,
                            mime_type="text/markdown",
                            source_url=web_url,
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "confluence",
                                "space_key": space_key,
                                "page_id": page_id,
                                "last_modified": when,
                            },
                        )
                    )
        except Exception as exc:
            logger.error("Failed to fetch documents from Confluence: %s", exc)

        return discovered

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        space_key = config.configuration.get("space_key", "")
        if not space_key:
            return [], state

        if config.configuration.get("offline_sandbox", False):
            docs = self._get_sandbox_documents(config)
            state.cursor = "2026-09-23T00:00:00Z"
            return docs, state

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        if not cloud_url:
            return [], state

        headers = self._get_headers(config)
        if not headers.get("Authorization"):
            return [], state

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                cql = f'space = "{space_key}" and type = "page"'
                if state.cursor:
                    cql += f' and lastModified > "{state.cursor}"'
                cql += " order by lastModified asc"

                url = (
                    f"{cloud_url}/wiki/rest/api/content/search"
                    f"?cql={httpx.URL('', params={'cql': cql}).params['cql']}"
                    f"&expand=body.storage,version,restrictions.read.restrictions.user,restrictions.read.restrictions.group"
                    f"&limit=50"
                )
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    logger.error("Incremental Confluence API error %d: %s", res.status_code, res.text[:200])
                    return [], state

                pages = res.json().get("results", [])
                discovered: list[DiscoveredDocument] = []
                latest_mod = state.cursor or ""

                for page in pages:
                    page_id = page.get("id", "")
                    title = page.get("title", f"confluence_page_{page_id}")
                    when = page.get("version", {}).get("when", "")
                    if when and when > latest_mod:
                        latest_mod = when

                    raw_body = page.get("body", {}).get("storage", {}).get("value", "")
                    markdown_content = _html_to_markdown(raw_body) or f"# {title}\n\n*Page synced from Confluence.*"

                    allowed_users: list[str] = []
                    allowed_groups: list[str] = []
                    is_public = True

                    read_restrictions = page.get("restrictions", {}).get("read", {}).get("restrictions", {})
                    for u in read_restrictions.get("user", {}).get("results", []):
                        u_id = u.get("email") or u.get("accountId")
                        if u_id:
                            allowed_users.append(u_id)
                    for g in read_restrictions.get("group", {}).get("results", []):
                        g_name = g.get("name")
                        if g_name:
                            allowed_groups.append(g_name)

                    if allowed_users or allowed_groups:
                        is_public = False

                    filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', title).lower()}_{page_id}.md"
                    discovered.append(
                        DiscoveredDocument(
                            filename=filename,
                            content=markdown_content,
                            mime_type="text/markdown",
                            source_url=f"{cloud_url}/wiki/spaces/{space_key}/pages/{page_id}",
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "confluence",
                                "space_key": space_key,
                                "page_id": page_id,
                                "last_modified": when,
                            },
                        )
                    )

                if latest_mod:
                    state.cursor = latest_mod
                return discovered, state
        except Exception as exc:
            logger.error("Incremental Confluence sync failed: %s", exc)
            return [], state


class JiraConnector(BaseConnector):
    """Production-grade Atlassian Jira Software Cloud Connector.

    Supports:
    - Basic auth (email + API token) or OAuth bearer token.
    - Querying issues via JQL (project, sprint, status, updated date).
    - Synthesizing complete issue threads with status, assignee, priority, description, and comments.
    - Issue security level and project group ACL extraction.
    - Incremental differential sync via JQL updated >= cursor.
    """

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            connector_type="jira",
            name="Atlassian Jira Software Cloud",
            description="Extracts Jira issues, requirements, sprint tickets, and comments with project ACLs.",
            icon="check-circle",
            supports_incremental=True,
            required_parameters=["cloud_url", "email", "api_token", "project_key"],
            optional_parameters={"jql_filter": "", "max_issues": 100},
        )

    def _get_headers(self, config: ConnectorConfig) -> dict[str, str]:
        email = config.configuration.get("email", "")
        api_token = config.configuration.get("api_token", "")
        access_token = config.configuration.get("access_token", "")

        headers = {"Accept": "application/json"}
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        elif email and api_token:
            basic = base64.b64encode(f"{email}:{api_token}".encode()).decode("utf-8")
            headers["Authorization"] = f"Basic {basic}"
        return headers

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        project_key = config.configuration.get("project_key")
        if not project_key:
            return False

        if config.configuration.get("offline_sandbox", False):
            return True

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        headers = self._get_headers(config)
        if not cloud_url or not headers.get("Authorization"):
            return False

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(f"{cloud_url}/rest/api/3/project/{project_key}", headers=headers)
                return res.status_code in (200, 404)
        except Exception as exc:
            logger.warning("Jira credential validation error: %s", exc)
            return False

    def _get_sandbox_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        project_key = config.configuration.get("project_key", "PROJ")
        cloud_url = config.configuration.get("cloud_url", "https://enterprise.atlassian.net").rstrip("/")
        return [
            DiscoveredDocument(
                filename=f"{project_key}-101_oauth_gateway.md",
                content=(
                    f"# [{project_key}-101] Implement Multi-Tenant OAuth Gateway\n\n"
                    f"**Project:** {project_key} | **Type:** Story | **Status:** In Progress\n"
                    f"**Assignee:** alice@corp.internal | **Reporter:** bob@corp.internal | **Priority:** High\n\n"
                    "## Description\n"
                    "Implement PKCE OAuth 2.0 authorization code grant flow with tenant claim validation.\n\n"
                    "## Comments\n"
                    "- **alice@corp.internal** (2026-09-20T10:00:00Z): Security middleware implemented and passing test suite.\n"
                    "- **sec-reviewer@corp.internal** (2026-09-21T15:30:00Z): Validated token expiration and session cookie attributes.\n"
                ),
                mime_type="text/markdown",
                source_url=f"{cloud_url}/browse/{project_key}-101",
                allowed_users=["alice@corp.internal", "bob@corp.internal"],
                allowed_groups=[f"jira-developers-{project_key.lower()}"],
                is_public=False,
                metadata={
                    "connector_id": config.id,
                    "source": "jira",
                    "project_key": project_key,
                    "issue_key": f"{project_key}-101",
                    "sync_mode": "sandbox",
                },
            ),
            DiscoveredDocument(
                filename=f"{project_key}-102_public_doc_portal.md",
                content=(
                    f"# [{project_key}-102] Public Developer API Documentation Release\n\n"
                    f"**Project:** {project_key} | **Type:** Task | **Status:** Done\n"
                    f"**Assignee:** docs-team@corp.internal | **Reporter:** product@corp.internal | **Priority:** Medium\n\n"
                    "## Description\n"
                    "Publish open OpenAPI / Swagger specs for tenant developers.\n"
                    "This specification is public."
                ),
                mime_type="text/markdown",
                source_url=f"{cloud_url}/browse/{project_key}-102",
                allowed_users=[],
                allowed_groups=[],
                is_public=True,
                metadata={
                    "connector_id": config.id,
                    "source": "jira",
                    "project_key": project_key,
                    "issue_key": f"{project_key}-102",
                    "sync_mode": "sandbox",
                },
            ),
        ]

    @staticmethod
    def _format_issue_markdown(issue: dict[str, Any], cloud_url: str) -> tuple[str, list[str], list[str], bool]:
        key = issue.get("key", "UNKNOWN")
        fields = issue.get("fields", {})
        rendered = issue.get("renderedFields", {})

        summary = fields.get("summary", "No Summary")
        status = fields.get("status", {}).get("name", "Unknown")
        issue_type = fields.get("issuetype", {}).get("name", "Task")
        priority = fields.get("priority", {}).get("name", "None")

        assignee = fields.get("assignee") or {}
        assignee_name = assignee.get("displayName") or assignee.get("emailAddress") or "Unassigned"
        assignee_id = assignee.get("emailAddress") or assignee.get("accountId") or ""

        reporter = fields.get("reporter") or {}
        reporter_name = reporter.get("displayName") or reporter.get("emailAddress") or "Unknown"
        reporter_id = reporter.get("emailAddress") or reporter.get("accountId") or ""

        created = fields.get("created", "")
        updated = fields.get("updated", "")

        desc_raw = rendered.get("description") or fields.get("description") or ""
        if isinstance(desc_raw, str):
            desc_md = _html_to_markdown(desc_raw) if "<" in desc_raw else desc_raw
        else:
            desc_md = str(desc_raw)

        # Comments
        comments_list = fields.get("comment", {}).get("comments", [])
        rendered_comments = rendered.get("comment", {}).get("comments", [])
        comments_md_lines: list[str] = []

        for idx, c in enumerate(comments_list):
            author = c.get("author", {}).get("displayName", "User")
            c_date = c.get("created", "")
            raw_c = ""
            if idx < len(rendered_comments):
                raw_c = rendered_comments[idx].get("body", "")
            if not raw_c:
                raw_c = c.get("body", "")

            if isinstance(raw_c, str):
                c_body = _html_to_markdown(raw_c) if "<" in raw_c else raw_c
            else:
                c_body = str(raw_c)

            comments_md_lines.append(f"- **{author}** ({c_date}):\n  {c_body.strip()}")

        comments_section = (
            "## Comments\n" + "\n\n".join(comments_md_lines) if comments_md_lines else "*No comments recorded.*"
        )

        md_content = (
            f"# [{key}] {summary}\n\n"
            f"**Key:** {key} | **Type:** {issue_type} | **Status:** {status} | **Priority:** {priority}\n"
            f"**Assignee:** {assignee_name} | **Reporter:** {reporter_name}\n"
            f"**Created:** {created} | **Updated:** {updated}\n\n"
            f"## Description\n{desc_md.strip()}\n\n"
            f"{comments_section}\n"
        )

        # Security & ACL
        security_level = fields.get("security")
        project_key = fields.get("project", {}).get("key", "").lower()
        allowed_users: list[str] = []
        allowed_groups: list[str] = []
        is_public = True

        if assignee_id:
            allowed_users.append(assignee_id)
        if reporter_id and reporter_id not in allowed_users:
            allowed_users.append(reporter_id)

        if project_key:
            allowed_groups.append(f"jira-project-{project_key}")

        if security_level:
            is_public = False
            sec_name = security_level.get("name", "")
            if sec_name:
                allowed_groups.append(f"jira-security-{sec_name.lower().replace(' ', '-')}")

        return md_content, allowed_users, allowed_groups, is_public

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        project_key = config.configuration.get("project_key", "")
        if not project_key:
            logger.warning("Jira connector '%s' missing project_key", config.id)
            return []

        if config.configuration.get("offline_sandbox", False):
            return self._get_sandbox_documents(config)

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        if not cloud_url:
            logger.warning("Jira connector '%s' missing cloud_url", config.id)
            return []

        headers = self._get_headers(config)
        if not headers.get("Authorization"):
            logger.error("Jira connector '%s' missing credentials", config.id)
            return []

        discovered: list[DiscoveredDocument] = []
        custom_jql = config.configuration.get("jql_filter", "")
        jql = f'project = "{project_key}"'
        if custom_jql:
            jql += f" AND ({custom_jql})"
        jql += " ORDER BY updated DESC"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = (
                    f"{cloud_url}/rest/api/3/search"
                    f"?jql={httpx.URL('', params={'jql': jql}).params['jql']}"
                    f"&expand=renderedFields"
                    f"&maxResults=50"
                )
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    logger.error("Jira API returned HTTP %d: %s", res.status_code, res.text[:200])
                    return []

                issues = res.json().get("issues", [])
                for issue in issues:
                    key = issue.get("key", "TICKET")
                    content_md, allowed_users, allowed_groups, is_public = self._format_issue_markdown(issue, cloud_url)
                    updated = issue.get("fields", {}).get("updated", "")

                    discovered.append(
                        DiscoveredDocument(
                            filename=f"jira_{key.lower()}.md",
                            content=content_md,
                            mime_type="text/markdown",
                            source_url=f"{cloud_url}/browse/{key}",
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "jira",
                                "project_key": project_key,
                                "issue_key": key,
                                "updated": updated,
                            },
                        )
                    )
        except Exception as exc:
            logger.error("Failed to fetch documents from Jira: %s", exc)

        return discovered

    async def fetch_incremental(
        self, config: ConnectorConfig, state: ConnectorSyncState
    ) -> tuple[list[DiscoveredDocument], ConnectorSyncState]:
        project_key = config.configuration.get("project_key", "")
        if not project_key:
            return [], state

        if config.configuration.get("offline_sandbox", False):
            docs = self._get_sandbox_documents(config)
            state.cursor = "2026-09-23T00:00:00Z"
            return docs, state

        cloud_url = config.configuration.get("cloud_url", "").rstrip("/")
        if not cloud_url:
            return [], state

        headers = self._get_headers(config)
        if not headers.get("Authorization"):
            return [], state

        jql = f'project = "{project_key}"'
        if state.cursor:
            # Format: 'YYYY-MM-DD HH:mm' or 'YYYY-MM-DD'
            date_part = state.cursor[:16].replace("T", " ")
            jql += f' AND updated >= "{date_part}"'
        jql += " ORDER BY updated ASC"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = (
                    f"{cloud_url}/rest/api/3/search"
                    f"?jql={httpx.URL('', params={'jql': jql}).params['jql']}"
                    f"&expand=renderedFields"
                    f"&maxResults=50"
                )
                res = await client.get(url, headers=headers)
                if res.status_code != 200:
                    logger.error("Incremental Jira API returned HTTP %d: %s", res.status_code, res.text[:200])
                    return [], state

                issues = res.json().get("issues", [])
                discovered: list[DiscoveredDocument] = []
                latest_updated = state.cursor or ""

                for issue in issues:
                    key = issue.get("key", "TICKET")
                    updated = issue.get("fields", {}).get("updated", "")
                    if updated and updated > latest_updated:
                        latest_updated = updated

                    content_md, allowed_users, allowed_groups, is_public = self._format_issue_markdown(issue, cloud_url)
                    discovered.append(
                        DiscoveredDocument(
                            filename=f"jira_{key.lower()}.md",
                            content=content_md,
                            mime_type="text/markdown",
                            source_url=f"{cloud_url}/browse/{key}",
                            allowed_users=allowed_users,
                            allowed_groups=allowed_groups,
                            is_public=is_public,
                            metadata={
                                "connector_id": config.id,
                                "source": "jira",
                                "project_key": project_key,
                                "issue_key": key,
                                "updated": updated,
                            },
                        )
                    )

                if latest_updated:
                    state.cursor = latest_updated
                return discovered, state
        except Exception as exc:
            logger.error("Incremental Jira sync failed: %s", exc)
            return [], state
