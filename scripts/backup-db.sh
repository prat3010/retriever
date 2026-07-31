#!/usr/bin/env bash
# Nightly logical backup of tenant data over the Supabase transaction pooler.
#
# Why \copy per table: pg_dump needs session-scoped state and hangs/fails over
# pgbouncer transaction mode. \copy is a single statement (implicit transaction)
# so it is pooler-safe. Schema is NOT dumped here — it is rebuilt from alembic
# migrations (see restore procedure in DEPLOYMENT.md).
#
# Usage: backup-db.sh [/path/to/.env]   (default /opt/retriever/.env)
set -euo pipefail

ENV_FILE="${1:-/opt/retriever/.env}"
OUTDIR="$(dirname "$ENV_FILE")/backups"
LOGDIR="$(dirname "$ENV_FILE")/logs"
KEEP_DAYS=14

[ -f "$ENV_FILE" ] || { echo "env file not found: $ENV_FILE"; exit 1; }
mkdir -p "$OUTDIR" "$LOGDIR"

URL="$(grep '^DATABASE_URL=' "$ENV_FILE" | cut -d= -f2-)"
export PGPASSWORD="$(python3 -c "
import sys, urllib.parse
u = urllib.parse.urlsplit(sys.argv[1].replace('postgresql+asyncpg://', 'postgresql://'))
print(urllib.parse.unquote(u.password))
" "$URL")"
# keep user/host/port from the URL; force sslmode=require (pooler requirement)
PSQL_URL="$(python3 -c "
import sys, urllib.parse
u = urllib.parse.urlsplit(sys.argv[1].replace('postgresql+asyncpg://', 'postgresql://'))
print(f'postgresql://{u.username}@{u.hostname}:{u.port}{u.path}?sslmode=require')
" "$URL")"

DATE="$(date +%F-%H%M)"
MANIFEST="$OUTDIR/${DATE}.txt"
: > "$MANIFEST"

TABLES="$(psql "$PSQL_URL" -t -A -c "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename NOT LIKE 'pg%' ORDER BY 1;")"
[ -n "$TABLES" ] || { echo "no tables found — aborting"; exit 1; }

while IFS= read -r t; do
    [ -n "$t" ] || continue
    psql "$PSQL_URL" -c "\\copy (SELECT * FROM \"$t\") TO STDOUT WITH (FORMAT csv, HEADER)" 2>>"$LOGDIR/backup.log" \
        | gzip > "$OUTDIR/${DATE}-${t}.csv.gz"
    ROWS="$(gzip -dc "$OUTDIR/${DATE}-${t}.csv.gz" | wc -l)"
    printf '%s\t%s rows\n' "$t" "$((ROWS - 1))" >> "$MANIFEST"
done <<< "$TABLES"

find "$OUTDIR" -name "*.csv.gz" -mtime +"$KEEP_DAYS" -delete

echo "$(date -u +%FT%TZ) backup complete: $(echo "$TABLES" | wc -l | tr -d ' ') tables" >> "$LOGDIR/backup.log"
cat "$MANIFEST"
