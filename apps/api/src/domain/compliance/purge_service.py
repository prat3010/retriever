"""Domain service executing cascading hard deletions for GDPR compliance and right-to-be-forgotten requests."""

import logging

logger = logging.getLogger(__name__)


class HardPurgeService:
    """Executes multi-tier hard deletions across database, vector, graph, and storage layers."""

    def __init__(self, compliance_repo=None, graph_repository=None, storage_provider=None) -> None:
        self.repo = compliance_repo
        self.graph_repo = graph_repository
        self.storage = storage_provider

    async def hard_purge_document(self, tenant_id: str, document_id: str) -> dict[str, int]:
        """Permanently destroy all records associated with a document across all storage systems."""
        stats = {
            "chunks_purged": 0,
            "vectors_purged": 0,
            "cache_purged": 0,
            "graph_triples_purged": 0,
            "document_purged": 0,
        }

        if self.repo:
            chunks, vectors, doc_purged, storage_path = await self.repo.purge_document_db_records(
                tenant_id, document_id
            )
            stats["chunks_purged"] = chunks
            stats["vectors_purged"] = vectors
            stats["document_purged"] = doc_purged

            if self.storage and storage_path and storage_path != "memory":
                try:
                    await self.storage.delete_file(storage_path)
                except Exception as err:
                    logger.warning(f"Failed to delete physical file '{storage_path}' ({err}).")

        if self.graph_repo:
            try:
                g_deleted = await self.graph_repo.delete_document_triples(tenant_id, document_id)
                stats["graph_triples_purged"] = g_deleted
            except Exception as err:
                logger.warning(f"Failed to delete graph triples for document '{document_id}' ({err}).")

        return stats

    async def hard_purge_tenant_data(self, tenant_id: str) -> dict[str, int]:
        """GDPR Right-to-be-forgotten full tenant data destruction."""
        if self.repo:
            return await self.repo.purge_full_tenant_db(tenant_id)
        return {
            "documents_purged": 0,
            "chunks_purged": 0,
            "vectors_purged": 0,
            "cache_purged": 0,
            "graph_triples_purged": 0,
            "evaluations_purged": 0,
        }
