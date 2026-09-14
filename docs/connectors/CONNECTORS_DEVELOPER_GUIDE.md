# 🔌 Community Connectors Developer Guide

Welcome to the **Retriever Community Connectors SDK**! This guide walks you through authoring, testing, and registering custom enterprise data connectors to ingest external content into Retriever's multi-tenant vector knowledge base.

---

## 🏛️ Connector Architecture Overview

Every connector in Retriever inherits from the abstract base class `BaseConnector` in `apps/api/src/domain/abstractions/connector.py`:

```text
               External Service (API / Database / Cloud Bucket)
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │ BaseConnector Subclass      │
                      │  - fetch_incremental(state) │
                      └──────────────┬──────────────┘
                                     │ Yields Document models
                                     ▼
                      ┌─────────────────────────────┐
                      │ Document Chunking & Parsing │
                      │  - ChunkerFactory           │
                      └──────────────┬──────────────┘
                                     │
                                     ▼
                      ┌─────────────────────────────┐
                      │ Hybrid Vector & Term Index  │
                      │  - pgvector HNSW + BM25     │
                      └─────────────────────────────┘
```

---

## 🛠️ Step-by-Step: Writing a Custom Connector

Let's build an example connector that synchronizes articles from a CMS or blog REST API.

### Step 1: Subclass `BaseConnector` & Use `@register_connector`

Create a new file under `apps/api/src/domain/connectors/blog_cms.py`:

```python
from typing import Any
from datetime import datetime, timezone
import httpx

from apps.api.src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    ConnectorManifest,
    ConnectorSyncState,
)
from apps.api.src.domain.abstractions.ingestion import Document
from apps.api.src.domain.connectors.registry import register_connector


@register_connector("blog_cms")
class BlogCmsConnector(BaseConnector):
    """Community connector syncing articles from an external Blog CMS."""

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self.api_url = config.parameters.get("api_url", "https://api.example.com/posts")
        self.api_token = config.parameters.get("api_token", "")

    def get_manifest(self) -> ConnectorManifest:
        return ConnectorManifest(
            type="blog_cms",
            name="Blog CMS Connector",
            description="Ingests published articles and updates incrementally via published_at timestamp.",
            version="1.0.0",
            author="Community Contributor",
            supported_features=["incremental_sync", "markdown_parsing"],
            parameter_schema={
                "api_url": {"type": "string", "required": True, "description": "CMS API base URL"},
                "api_token": {"type": "string", "required": True, "secret": True},
                "batch_size": {"type": "integer", "default": 100},
            },
        )

    async def test_connection(self) -> bool:
        """Verify credentials and endpoint accessibility."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.api_url}/health", headers=headers)
            return resp.status_code == 200

    async def fetch_incremental(self, state: ConnectorSyncState) -> tuple[list[Document], ConnectorSyncState]:
        """Fetch documents mutated since state.watermark."""
        watermark = state.watermark or "1970-01-01T00:00:00Z"
        headers = {"Authorization": f"Bearer {self.api_token}"}
        params = {"since": watermark}

        documents: list[Document] = []
        newest_timestamp = watermark

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(self.api_url, headers=headers, params=params)
            resp.raise_for_status()
            posts = resp.json().get("posts", [])

            for post in posts:
                doc = Document(
                    tenant_id=self.config.tenant_id,
                    title=post["title"],
                    content=f"# {post['title']}\n\n{post['content']}",
                    source=f"blog:{post['id']}",
                    metadata={
                        "author": post.get("author"),
                        "published_at": post.get("published_at"),
                        "tags": post.get("tags", []),
                    },
                )
                documents.append(doc)
                if post.get("published_at", "") > newest_timestamp:
                    newest_timestamp = post["published_at"]

        # Advance state
        new_state = state.model_copy(deep=True)
        new_state.watermark = newest_timestamp
        new_state.last_sync_at = datetime.now(timezone.utc).isoformat()
        return documents, new_state
```

---

## 🧪 Testing Your Connector

Write a unit test in `apps/api/tests/test_custom_connector.py` using `unittest.mock` or `respx`:

```python
import pytest
from apps.api.src.domain.connectors.registry import ConnectorRegistry
from apps.api.src.domain.abstractions.connector import ConnectorConfig, ConnectorSyncState

@pytest.mark.asyncio
async def test_blog_cms_manifest():
    connector_cls = ConnectorRegistry.get("blog_cms")
    assert connector_cls is not None
    
    config = ConnectorConfig(
        connector_id="test_conn",
        tenant_id="test_tenant",
        connector_type="blog_cms",
        parameters={"api_url": "https://api.test.com", "api_token": "secret"},
    )
    connector = connector_cls(config)
    manifest = connector.get_manifest()
    assert manifest.type == "blog_cms"
    assert "api_url" in manifest.parameter_schema
```

Run tests:
```bash
pytest apps/api/tests/test_custom_connector.py -v
```

---

## 🚢 Publishing Your Connector

1. Place your connector in `apps/api/src/domain/connectors/`.
2. Import it in `apps/api/src/domain/connectors/__init__.py`.
3. Submit a pull request to [`github.com/prat3010/retriever`](https://github.com/prat3010/retriever).
