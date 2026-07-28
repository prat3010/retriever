"""Script to batch process all PENDING documents across tenants."""
import argparse
import asyncio
import logging

import httpx

from src.config import settings
from src.container import (
    document_repository,
    ingest_file_sync,
    local_storage,
    search_service,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("process_pending")


async def process_all_pending(target_engine: str = "laptop") -> None:
    logger.info("Scanning for PENDING documents across all tenants...")
    # Fetch all pending documents
    # Using bypass_rls=True to retrieve pending documents across tenants
    pending_docs = await document_repository.list_documents(tenant_id="*", bypass_rls=True)
    pending_docs = [d for d in pending_docs if d.status == "PENDING"]

    if not pending_docs:
        logger.info("No PENDING documents found.")
        return

    logger.info("Found %d PENDING document(s) to process via target_engine='%s'.", len(pending_docs), target_engine)

    processed_count = 0
    failed_count = 0

    for doc in pending_docs:
        logger.info("Processing document '%s' (ID: %s, Tenant: %s)...", doc.filename, doc.document_id, doc.tenant_id)
        doc.status = "PROCESSING"
        await document_repository.create_document(doc.tenant_id, doc)

        file_content = await local_storage.read_file(doc.storage_path)
        if file_content is None and settings.REMOTE_STORAGE_API_URL:
            try:
                remote_url = f"{settings.REMOTE_STORAGE_API_URL.rstrip('/')}/v1/admin/tenants/{doc.tenant_id}/documents/{doc.document_id}/file"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    res = await client.get(
                        remote_url,
                        headers={"X-Admin-Master-Key": settings.ADMIN_MASTER_KEY},
                    )
                    if res.status_code == 200:
                        file_content = res.content
            except Exception as e:
                logger.warning("Failed remote HTTP fetch for %s: %s", doc.document_id, e)

        if file_content is None:
            logger.error("Could not retrieve file bytes for document %s.", doc.document_id)
            doc.status = "FAILED"
            await document_repository.create_document(doc.tenant_id, doc)
            failed_count += 1
            continue

        try:
            chunk_count = await ingest_file_sync(
                tenant_id=doc.tenant_id,
                document_id=doc.document_id,
                filename=doc.filename,
                file_content=file_content,
                file_hash=doc.file_hash,
                mime_type=doc.mime_type,
                embedder=search_service.embedder,
            )
            logger.info("Successfully indexed '%s' (%d chunks).", doc.filename, chunk_count)
            processed_count += 1
        except Exception as err:
            logger.error("Error processing document %s: %s", doc.document_id, err)
            doc.status = "FAILED"
            await document_repository.create_document(doc.tenant_id, doc)
            failed_count += 1

    logger.info("Batch completed: %d processed, %d failed.", processed_count, failed_count)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process PENDING documents across all tenants.")
    parser.add_argument(
        "--target",
        choices=["laptop", "oracle", "auto"],
        default="laptop",
        help="Target processing engine (default: laptop)",
    )
    args = parser.parse_args()
    asyncio.run(process_all_pending(target_engine=args.target))


if __name__ == "__main__":
    main()
