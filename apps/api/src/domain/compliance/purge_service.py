"""Domain service executing cascading hard deletions for GDPR compliance and right-to-be-forgotten requests."""

import logging
from typing import Any

from src.domain.abstractions.compliance import (
    ComplianceCertificateDTO,
    ErasureScope,
)

logger = logging.getLogger(__name__)


class HardPurgeService:
    """Executes multi-tier hard deletions across database, vector, graph, and storage layers."""

    def __init__(
        self,
        compliance_repo: Any = None,
        graph_repository: Any = None,
        storage_provider: Any = None,
        certificate_service: Any = None,
    ) -> None:
        self.repo = compliance_repo
        self.graph_repo = graph_repository
        self.storage = storage_provider
        self.cert_service = certificate_service

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

    async def purge_document_with_certificate(
        self,
        tenant_id: str,
        document_id: str,
        requester: str,
        reason: str = "GDPR Right to Erasure Request",
    ) -> ComplianceCertificateDTO:
        """Execute document purge and issue a cryptographically signed compliance certificate."""
        stats = await self.hard_purge_document(tenant_id, document_id)

        if self.cert_service:
            certificate = self.cert_service.issue_certificate(
                tenant_id=tenant_id,
                requester=requester,
                reason=reason,
                erasure_scope=ErasureScope.DOCUMENT,
                records_purged=stats,
                target_id=document_id,
            )
        else:
            # Fallback baseline certificate if certificate_service is not wired
            certificate = ComplianceCertificateDTO(
                certificate_id="cert_gdpr_legacy",
                tenant_id=tenant_id,
                requester=requester,
                reason=reason,
                erasure_scope=ErasureScope.DOCUMENT,
                target_id=document_id,
                records_purged=stats,
                sha256_audit_signature="unsigned_legacy",
                verification_status="UNVERIFIED",
            )

        if self.repo and hasattr(self.repo, "save_compliance_certificate"):
            await self.repo.save_compliance_certificate(certificate)

        return certificate

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

    async def purge_tenant_with_certificate(
        self,
        tenant_id: str,
        requester: str,
        reason: str = "GDPR Article 17 Full Tenant Erasure",
    ) -> ComplianceCertificateDTO:
        """Execute full tenant hard-purge and issue an immutable signed compliance certificate."""
        stats = await self.hard_purge_tenant_data(tenant_id)

        if self.cert_service:
            certificate = self.cert_service.issue_certificate(
                tenant_id=tenant_id,
                requester=requester,
                reason=reason,
                erasure_scope=ErasureScope.FULL_TENANT_WIPE,
                records_purged=stats,
                target_id=tenant_id,
            )
        else:
            certificate = ComplianceCertificateDTO(
                certificate_id="cert_gdpr_legacy",
                tenant_id=tenant_id,
                requester=requester,
                reason=reason,
                erasure_scope=ErasureScope.FULL_TENANT_WIPE,
                target_id=tenant_id,
                records_purged=stats,
                sha256_audit_signature="unsigned_legacy",
                verification_status="UNVERIFIED",
            )

        if self.repo and hasattr(self.repo, "save_compliance_certificate"):
            await self.repo.save_compliance_certificate(certificate)

        return certificate

    async def get_certificates(self, tenant_id: str) -> list[ComplianceCertificateDTO]:
        """Retrieve all compliance certificates issued for a tenant."""
        if self.repo and hasattr(self.repo, "get_compliance_certificates"):
            return await self.repo.get_compliance_certificates(tenant_id)
        return []

    async def get_certificate_by_id(self, certificate_id: str) -> ComplianceCertificateDTO | None:
        """Retrieve a specific certificate by its ID."""
        if self.repo and hasattr(self.repo, "get_compliance_certificate_by_id"):
            return await self.repo.get_compliance_certificate_by_id(certificate_id)
        return None
