#!/bin/bash
set -e

WAYMARK_DIR="/root/waymark"
source "${WAYMARK_DIR}/.env"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/tmp/waymark_${TIMESTAMP}.sql.gz"
R2_KEY="backups/waymark_${TIMESTAMP}.sql.gz"
R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "[$(date)] Starting database backup..."

# Dump and gzip
docker compose -f "${WAYMARK_DIR}/docker-compose.yml" exec -T postgres \
    pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_FILE}"

SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Dump complete: ${BACKUP_FILE} (${SIZE})"

# Upload to R2
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
aws s3 cp "${BACKUP_FILE}" "s3://${R2_BUCKET_NAME}/${R2_KEY}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --region auto \
    --no-progress

echo "[$(date)] Uploaded to R2: ${R2_KEY}"

# Remove local temp file
rm -f "${BACKUP_FILE}"
echo "[$(date)] Backup finished successfully."
