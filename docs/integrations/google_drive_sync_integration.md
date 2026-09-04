# Integration Guide: Google Drive 2-Way Knowledge Sync

**Platform Surface:** Google Drive & Google Workspace Cloud Storage  
**Milestone:** 90 (Phase K)  
**Status:** Production Ready  

---

## 1. Overview & Capabilities

The **Google Drive 2-Way Sync** integration automatically monitors a designated Google Drive folder, ingesting new or modified documents (PDFs, Docs, Spreadsheets) into the tenant's vector store and soft-deleting vector records when files are removed from the folder.

### Key Capabilities:
1. **Differential Webhook Sync**: Receives push notifications from Google Drive Changes API upon file edits.
2. **Format Conversion Pipeline**: Auto-converts Google Docs to clean markdown and Google Sheets to tabular structured chunks.
3. **Automated Vector Lifecycle**: Edits to a file trigger atomic re-chunking and re-embedding without duplicating index entries.

---

## 2. Google Cloud Service Account Setup

1. Open **Google Cloud Console** and navigate to your project.
2. Enable the **Google Drive API**.
3. Create a **Service Account** with the name `retriever-gdrive-sync`.
4. Create a JSON Service Account Key and store it securely on your server:
   ```bash
   /etc/retriever/gdrive-credentials.json
   ```
5. Share your target Google Drive folder with the Service Account email address (`retriever-gdrive-sync@<project-id>.iam.gserviceaccount.com`) granting `Viewer` permissions.

---

## 3. Configuration

Set environment variables in your server configuration:
```bash
GDRIVE_SERVICE_ACCOUNT_FILE="/etc/retriever/gdrive-credentials.json"
GDRIVE_SYNC_INTERVAL_SECONDS=300 # Poll / webhook delta check every 5 minutes
```

---

## 4. Manual Sync & Webhook Trigger

To manually trigger a synchronization run for a tenant's configured Google Drive folder:
```bash
curl -X POST "https://rag.prateeq.in/v1/connectors/{connectorId}/sync" \
  -H "Authorization: Bearer $TENANT_API_KEY"
```
The sync job executes in the background via Celery, emitting progress logs to the Admin Dashboard and SaaS Studio.
