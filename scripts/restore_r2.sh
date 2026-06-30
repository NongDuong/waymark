#!/bin/bash
set -e

WAYMARK_DIR="/root/waymark"
source "${WAYMARK_DIR}/.env"

R2_ENDPOINT="https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

echo "[$(date)] Listing available backups..."

# List all backups sorted by date (newest first)
AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
aws s3 ls "s3://${R2_BUCKET_NAME}/backups/" \
    --endpoint-url "${R2_ENDPOINT}" \
    --region auto | sort -r | head -20

echo ""
echo "Enter backup filename to restore (e.g. waymark_20260630_110853.sql.gz):"
read -r BACKUP_FILENAME

if [ -z "${BACKUP_FILENAME}" ]; then
    echo "No filename entered. Exiting."
    exit 1
fi

LOCAL_FILE="/tmp/${BACKUP_FILENAME}"
R2_KEY="backups/${BACKUP_FILENAME}"

echo "[$(date)] Downloading ${R2_KEY} from R2..."

AWS_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
AWS_SECRET_ACCESS_KEY="${R2_SECRET_ACCESS_KEY}" \
aws s3 cp "s3://${R2_BUCKET_NAME}/${R2_KEY}" "${LOCAL_FILE}" \
    --endpoint-url "${R2_ENDPOINT}" \
    --region auto

echo "[$(date)] Download complete. Restoring to database..."

# Drop all tables and restore
docker compose -f "${WAYMARK_DIR}/docker-compose.yml" exec -T postgres \
    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

gunzip -c "${LOCAL_FILE}" | \
    docker compose -f "${WAYMARK_DIR}/docker-compose.yml" exec -T postgres \
    psql -U "${POSTGRES_USER}" "${POSTGRES_DB}"

rm -f "${LOCAL_FILE}"
echo "[$(date)] Restore complete."
