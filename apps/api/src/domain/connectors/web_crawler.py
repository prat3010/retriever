import re

import httpx

from src.domain.abstractions.connector import (
    BaseConnector,
    ConnectorConfig,
    DiscoveredDocument,
)


class WebCrawlerConnector(BaseConnector):
    """Web crawler connector for fetching and parsing web documents."""

    async def validate_credentials(self, config: ConnectorConfig) -> bool:
        start_url = config.configuration.get("start_url")
        return bool(start_url and (start_url.startswith("http://") or start_url.startswith("https://")))

    async def fetch_documents(self, config: ConnectorConfig) -> list[DiscoveredDocument]:
        start_url = config.configuration.get("start_url")
        max_depth = config.configuration.get("max_depth", 1)

        if not start_url:
            return []

        documents: list[DiscoveredDocument] = []
        visited: set[str] = set()

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            queue: list[tuple[str, int]] = [(start_url, 0)]

            while queue:
                curr_url, depth = queue.pop(0)
                if curr_url in visited or depth > max_depth:
                    continue

                visited.add(curr_url)

                try:
                    res = await client.get(curr_url)
                    if res.status_code == 200:
                        raw_html = res.text
                        # Strip simple HTML tags to plain text
                        plain_text = re.sub(r"<[^>]+>", " ", raw_html)
                        plain_text = re.sub(r"\s+", " ", plain_text).strip()

                        filename = f"crawled_{len(visited)}.txt"
                        documents.append(
                            DiscoveredDocument(
                                filename=filename,
                                content=plain_text,
                                mime_type="text/plain",
                                source_url=curr_url,
                                metadata={
                                    "connector_id": config.id,
                                    "source": "web_crawler",
                                    "depth": depth,
                                },
                            )
                        )
                except Exception:
                    # Continue crawling remaining URLs if one fails
                    pass

        return documents
