# 💾 Disaster Recovery, Cloud Snapshots & Point-in-Time Recovery (PITR) Guide

This guide explains how Retriever's automated backup, cryptographic encryption, and disaster recovery engine works, and how to configure off-site cloud archival (Cloudflare R2, AWS S3, or MinIO).

---

## 1. Overview: How Backups Work

Retriever features an enterprise-grade, pooler-safe database backup and recovery pipeline:
- **Default Mode (Zero Cloud Dependency):** Backups are dumped from PostgreSQL using single-statement, pooler-safe queries, compressed with Gzip, encrypted locally using **AES-256 GCM**, and saved to `/tmp/retriever/backups/` (or your configured `LOCAL_BACKUP_DIR`).
- **Cloud Archival Mode:** When S3/R2 credentials are provided, encrypted archives and signed SHA-256 metadata manifests are automatically streamed to off-site cloud object storage.
- **Topological Integrity:** Restorations respect database foreign key dependencies (`tenants` $\rightarrow$ `users` $\rightarrow$ `documents` $\rightarrow$ `vector_records`).
- **Dry-Run Audit Safety:** Any snapshot can be cryptographically verified and schema-audited in milliseconds without modifying live database tables.

---

## 2. Default Local Storage (No Account Needed)

If you do not configure any cloud credentials, Retriever works **100% out of the box** using local storage:

```bash
# 1. Trigger an immediate encrypted snapshot
python3 scripts/db_snapshot.py

# Output:
# ✅ DATABASE SNAPSHOT COMPLETED SUCCESSFULLY
# Snapshot ID    : snap_20260904_120000
# Tables Dumped  : 17
# Encrypted Size : 420 bytes
# SHA-256 Digest : 4a27d1dec4...
# Storage URI    : file:///tmp/retriever/backups/snap_20260904_120000.tar.gz.enc
```

---

## 3. How to Enable Cloud Storage (Cloudflare R2 / AWS S3 / MinIO)

To protect against physical VPS crashes or disk failures, you can mirror encrypted snapshots to off-site cloud storage. 

Set the following variables in your `.env` file:

### Option A: Cloudflare R2 (Recommended — 10GB Free Storage, Zero Egress Fees)
1. In the Cloudflare Dashboard, go to **R2 Object Storage** $\rightarrow$ **Create Bucket** (e.g. `retriever-backups`).
2. Go to **Manage R2 API Tokens** $\rightarrow$ **Create API Token** (Permissions: Object Read & Write).
3. Copy your Account ID, Access Key ID, and Secret Access Key.
4. Add to `.env`:
```env
STORAGE_PROVIDER="s3"
STORAGE_BUCKET="retriever-backups"
AWS_ACCESS_KEY_ID="<your-cloudflare-r2-access-key-id>"
AWS_SECRET_ACCESS_KEY="<your-cloudflare-r2-secret-access-key>"
S3_ENDPOINT_URL="https://<your-cloudflare-account-id>.r2.cloudflarestorage.com"
AWS_REGION="auto"
```

### Option B: Amazon Web Services (AWS S3)
1. In the AWS Console, create an S3 bucket (e.g. `retriever-enterprise-backups`).
2. Create an IAM user with `s3:PutObject`, `s3:GetObject`, and `s3:ListBucket` permissions.
3. Add to `.env`:
```env
STORAGE_PROVIDER="s3"
STORAGE_BUCKET="retriever-enterprise-backups"
AWS_ACCESS_KEY_ID="<your-aws-access-key-id>"
AWS_SECRET_ACCESS_KEY="<your-aws-secret-access-key>"
AWS_REGION="us-east-1"
```

### Option C: MinIO (100% Free Self-Hosted S3)
If you want S3-compatible cloud storage without creating cloud accounts:
```bash
docker run -d -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=retriever_admin" \
  -e "MINIO_ROOT_PASSWORD=retriever_secret" \
  minio/minio server /data --console-address ":9001"
```
Then add to `.env`:
```env
STORAGE_PROVIDER="s3"
STORAGE_BUCKET="retriever-backups"
AWS_ACCESS_KEY_ID="retriever_admin"
AWS_SECRET_ACCESS_KEY="retriever_secret"
S3_ENDPOINT_URL="http://localhost:9000"
AWS_REGION="us-east-1"
```

---

## 4. Disaster Recovery & Restoring from a Snapshot

### Step 1: Run a Non-Destructive Dry-Run Audit
Before restoring, always verify that the snapshot archive is intact and uncorrupted:

```bash
python3 scripts/db_restore.py --snapshot snap_20260904_120000 --dry-run
```
This will:
1. Verify the archive's SHA-256 digest against the signed manifest.
2. Decrypt the AES-256 GCM payload into memory.
3. Validate table structure and row counts across all 17 tables.
4. **Leave the live database 100% untouched.**

### Step 2: Execute Live Database Restoration
When you are ready to restore:

```bash
python3 scripts/db_restore.py --snapshot snap_20260904_120000 --execute
```
This will:
1. Open a transaction-safe database connection.
2. Traverse tables in dependency order (`tenants` $\rightarrow$ `users` $\rightarrow$ `documents` $\rightarrow$ `vector_records`).
3. Insert missing records with `ON CONFLICT DO NOTHING`.
4. Commit the transaction atomically.

---

## 5. Automating Daily Backups (Cron & Systemd)

To schedule automatic nightly backups at 3:00 AM UTC:

### Via Crontab (`crontab -e`):
```bash
0 3 * * * cd /opt/retriever && uv run python3 scripts/db_snapshot.py >> /var/log/retriever-backup.log 2>&1
```

### Via Systemd Timer:
Create `/etc/systemd/system/retriever-backup.service`:
```ini
[Unit]
Description=Retriever Encrypted Database Snapshot
After=network.target

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/opt/retriever
ExecStart=/opt/retriever/apps/api/.venv/bin/python3 scripts/db_snapshot.py
```

Create `/etc/systemd/system/retriever-backup.timer`:
```ini
[Unit]
Description=Run Retriever Backup Daily at 3AM UTC

[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```
Enable the timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now retriever-backup.timer
```
