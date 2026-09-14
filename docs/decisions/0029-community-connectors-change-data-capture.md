# ADR-029: Enterprise Change-Data-Capture (CDC) & Community Connectors Ecosystem

**Status:** Accepted  
**Date:** 2026-09-14  
**Deciders:** Principal Cognitive Systems Architects, Enterprise Integration Engineers, Data Platform Leads  
**Consulted:** SaaS Studio Team, FDE Integration Team  
**Informed:** Enterprise Clients, Open-Source Developer Community  

---

## 1. Context and Problem Statement

To power enterprise cognitive RAG, organizations require continuous, near-real-time ingestion from heterogeneous operational data silos—including relational OLTP databases (PostgreSQL, MySQL), cloud object stores (AWS S3, Cloudflare R2, MinIO, Google Cloud Storage), and engineering workspace tools (GitHub, Slack).

Prior to Milestone 111:
1. **Batch Ingestion Bottlenecks:** Documents were ingested via manual single-file REST uploads or static directory scans, requiring full file re-processing.
2. **Heavyweight CDC Overhead:** Traditional CDC pipelines (e.g. Debezium, Kafka Connect) introduce substantial infrastructure complexity, JVM memory overhead, and separate operational clusters that violate Retriever's single-binary, un-bloated deployment ethos.
3. **Lack of Extensible Community SDK:** Third-party developers lacked a standardized, decorator-driven plugin interface to contribute new enterprise connectors without modifying core domain routing logic.

To resolve these challenges, Retriever introduced **Platform Battery #27: Enterprise CDC & Community Connectors Ecosystem** (`v1.1.0-alpha1`, Milestone 111).

---

## 2. Decision Drivers

- **Hexagonal Ingestion Abstractions:** Pure domain interfaces in `src/domain/abstractions/connector.py` (`BaseConnector`, `ConnectorConfig`, `ConnectorSyncState`, `ConnectorManifest`, `BaseDocumentParser`) ensuring complete decoupling from specific database drivers and cloud vendor SDKs.
- **High-Watermark Chronological Cursor Tracking:** Relational CDC tracks chronological monotonic watermarks (`updated_at > watermark`) without requiring database log decoding extensions (such as `test_decoding` or `wal2json`), allowing read-only replica connections across both PostgreSQL and MySQL:
  $$\Delta D = \{r \in T \mid r.\text{updated\_at} > \tau_{\text{watermark}}\}$$
- **Content ETag Checksum Differential Caching:** Object store connectors track MD5/ETag digests and `LastModified` timestamps in `ConnectorSyncState.metadata["seen_etags"]`, eliminating redundant network bandwidth and processing compute for unchanged files.
- **Dynamic Community Plugin Registration (`@register_connector`):** Standardized Python decorator registering connector classes into `ConnectorRegistry` at startup or runtime, generating self-describing parameter schemas for the Admin Dashboard and SaaS Studio.
- **Incremental State Persistence:** Synchronizations persist cursor state (`watermark`, `cursor`, `last_sync_at`) per tenant connector configuration in the PostgreSQL `configurations` table.

---

## 3. Decision Outcome

Implemented four enterprise connectors in `apps/api/src/domain/connectors/`:
1. `DatabaseCdcConnector` (`database_cdc.py`): Relational high-watermark replication formatting rows into Markdown with primary-key header blocks and attribute tables.
2. `S3StorageConnector` (`cloud_storage.py`): S3/R2/MinIO/GCS object store crawler with ETag diffing and prefix folder targeting.
3. `GitHubConnector` (`github.py`): Repository documentation, issues, and pull request sync with `since` ISO-8601 cursor tracking.
4. `SlackConnector` (`slack.py`): Threaded conversation aggregation with timestamp (`ts`) cursor tracking.

Exposed administrative and catalog APIs:
- `GET /v1/admin/connectors/manifests`: Returns connector descriptor schemas and default parameters.
- `POST /v1/admin/tenants/{tenantId}/connectors/{connectorId}/sync`: Dispatches incremental synchronizations and persists cursor updates.

Registered in `BatteryService` as **Battery #27 (`cdc_community_connectors`)**.

### Positive Consequences
- **Zero Heavyweight Infrastructure:** No Kafka, Zookeeper, or JVM brokers required; runs entirely within standard async Python background tasks.
- **Incremental Efficiency:** Only mutated database rows and altered cloud objects are ingested and embedded.
- **Open-Source Extensibility:** External developers can author custom enterprise connectors with under 100 lines of standard Python.
