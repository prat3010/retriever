# Enterprise Change-Data-Capture (CDC) & Community Connectors Ecosystem

**Milestone:** M111 (v1.1.0-alpha1)  
**System Layer:** Data Ingestion & System Extensibility (Platform Battery #27)  
**Architecture:** Monotonic High-Watermark CDC + Content ETag Diffing + Dynamic Plugin Decorator Registry  

---

## 1. Executive Summary

Milestone 111 registers **Platform Battery #27 (`cdc_community_connectors`)** under the `SYSTEM_EXTENSIBILITY` category.

In enterprise cognitive search, static file uploads represent a small fraction of organizational intelligence. Mission-critical business context is continuously generated across operational OLTP databases (customer records, inventory changes, ledger mutations), cloud bucket drops (PDFs, raw datasets), and developer workspace activity (GitHub pull requests, Slack channel threads).

Milestone 111 introduces an extensible, lightweight connector ecosystem:
- **Zero Heavyweight Brokers:** Operates without Debezium, Kafka, or JVM dependencies; pure async Python execution.
- **Relational Database CDC (`DatabaseCdcConnector`):** Queries mutated table records where `updated_at > watermark`, formats rows into structured Markdown documents with primary key banners and attribute tables, and advances high-watermark state.
- **Cloud Object Storage Watcher (`S3StorageConnector`):** Multi-cloud object crawler (AWS S3, Cloudflare R2, MinIO, GCS) with MD5/ETag checksum diffing, indexing only new or modified files.
- **Developer Workspace Connectors (`GitHubConnector`, `SlackConnector`):** Incremental sync with `since` ISO timestamps and Slack message `ts` watermark cursors.
- **Dynamic `@register_connector` Decorator:** Standardized plugin architecture allowing third-party developers to register custom data sources with automatic OpenAPI/UI descriptor manifest exposure.

---

## 2. Mathematical & Algorithmic Foundation

### Monotonic High-Watermark CDC
Given a relational table $T$ with monotonic watermark column $\tau_{\text{col}}$ (e.g. `updated_at`):
$$\Delta D_k = \left\{ r \in T \mid r.\tau_{\text{col}} > \tau_{\text{watermark}}^{(k-1)} \right\}$$
Upon successful vectorization and indexing of $\Delta D_k$, the watermark advances to:
$$\tau_{\text{watermark}}^{(k)} = \max_{r \in \Delta D_k} (r.\tau_{\text{col}})$$

### ETag Content Differential
For object store crawler $S$, let $\mathcal{E}$ represent the cache of known digests:
$$\mathcal{E} = \{ \text{digest}(obj) \mid obj \in \text{Seen} \}$$
A document $obj$ is ingested if and only if:
$$\text{ETag}(obj) \notin \mathcal{E} \quad \lor \quad \text{LastModified}(obj) > t_{\text{last\_scan}}$$

---

## 3. Battery Specifications & Parameters

### Battery Specification
- **Identifier:** `cdc_community_connectors`
- **Category:** `SYSTEM_EXTENSIBILITY`
- **Latency Profile:** `<15ms` polling & discovery overhead
- **Algorithm Foundation:** High-Watermark Transaction Log CDC, Object Store Event Ingestion & Incremental Cursor Reconciliation
- **Health Check Endpoint:** `/v1/admin/connectors/manifests`

### Supported Connector Types
1. `database_cdc`: PostgreSQL and MySQL high-watermark CDC.
2. `s3`: AWS S3, Cloudflare R2, MinIO, and GCS object storage watcher.
3. `github`: Repository documentation, issues, and pull requests.
4. `slack`: Public/private channel message history and thread discussions.
5. `notion`: Notion workspace pages and databases.
6. `google_drive`: Google Drive folder sync.
7. `web_crawler`: Recursive domain web crawler with robots.txt compliance.
8. `local_folder`: Local filesystem directory watcher.

---

## 4. Verification & Testing

Validated by automated test suite in `apps/api/tests/test_community_connectors.py`:
- 10/10 tests passing covering database CDC row formatting, high-watermark advancement, S3 ETag caching, GitHub/Slack cursor tracking, and dynamic registry manifest reflection.
