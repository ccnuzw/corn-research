#!/usr/bin/env bash
# Run from cron as the deployment user. Stop application writers first.
set -euo pipefail
umask 077

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"
ENV_FILE=${ENV_FILE:-.env.production}
BACKUP_DIR=${BACKUP_DIR:-"$ROOT/backups"}
COMPOSE=(docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml)
mkdir -p "$BACKUP_DIR"
LOCK="$BACKUP_DIR/.backup-lock"
if ! mkdir "$LOCK" 2>/dev/null; then
    echo "Backup already running (or stale lock): $LOCK" >&2
    exit 1
fi
STAGING=""
cleanup() {
    # Retain incomplete data for diagnosis; it never gets a success manifest.
    rmdir "$LOCK"
}
trap cleanup EXIT

# Excluding the gateway is insufficient: workers and scheduler write in backend.
if [[ -n "$("${COMPOSE[@]}" ps --status running -q backend)" ]]; then
    echo "Stop backend and all external writers before backup." >&2
    exit 1
fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
STAGING="$BACKUP_DIR/.incomplete-$STAMP-$$"
mkdir "$STAGING"
"${COMPOSE[@]}" exec -T postgres sh -ec \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-acl' \
    > "$STAGING/postgres.dump"
"${COMPOSE[@]}" exec -T redis redis-cli --rdb /tmp/corn-backup.rdb >&2
"${COMPOSE[@]}" cp redis:/tmp/corn-backup.rdb "$STAGING/redis.rdb" >&2
"${COMPOSE[@]}" exec -T redis rm /tmp/corn-backup.rdb
tar -czf "$STAGING/html-data.tar.gz" -C "$ROOT" data
git rev-parse HEAD > "$STAGING/code-version.txt"
"${COMPOSE[@]}" images -q > "$STAGING/image-ids.txt"
python3 - "$STAGING" <<'PY'
import hashlib
import json
from pathlib import Path
import sys

directory = Path(sys.argv[1])
checksums = {}
for path in sorted(directory.iterdir()):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    checksums[path.name] = digest.hexdigest()
(directory / 'manifest.json').write_text(json.dumps(checksums, indent=2) + '\n')
PY
FINAL="$BACKUP_DIR/$STAMP-$$"
mv "$STAGING" "$FINAL"
echo "Backup complete: $FINAL"
echo "Encrypt, copy off-host, verify checksums, then resume backend. No automatic deletion."
