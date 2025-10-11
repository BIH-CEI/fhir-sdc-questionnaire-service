#!/bin/bash
# PostgreSQL backup script for FHIR Form Manager
# HAPI FHIR will automatically reindex on restore

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/fhir_backup_$DATE.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup at $(date)"
echo "Backup location: $BACKUP_FILE"

# Create compressed PostgreSQL dump
pg_dump -h "${PGHOST:-db}" \
        -p "${PGPORT:-5432}" \
        -U "${PGUSER}" \
        -d "${PGDATABASE}" \
        --no-owner \
        --no-acl \
        | gzip > "$BACKUP_FILE"

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup completed successfully: $SIZE"
else
    echo "ERROR: Backup file was not created!"
    exit 1
fi

# Clean up old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "fhir_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# List remaining backups
echo "Available backups:"
ls -lh "$BACKUP_DIR"/fhir_backup_*.sql.gz 2>/dev/null || echo "No backups found"

echo "Backup completed at $(date)"
