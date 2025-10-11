#!/bin/bash
# PostgreSQL restore script for FHIR Form Manager
# After restore, HAPI FHIR will automatically reindex all resources

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /backups/fhir_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=========================================="
echo "WARNING: This will restore the database!"
echo "All current data will be replaced."
echo "=========================================="
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo "Starting restore at $(date)"

# Drop existing database and recreate
echo "Dropping and recreating database..."
psql -h "${PGHOST:-db}" \
     -p "${PGPORT:-5432}" \
     -U "${PGUSER}" \
     -d postgres \
     -c "DROP DATABASE IF EXISTS ${PGDATABASE};"

psql -h "${PGHOST:-db}" \
     -p "${PGPORT:-5432}" \
     -U "${PGUSER}" \
     -d postgres \
     -c "CREATE DATABASE ${PGDATABASE};"

# Restore from backup
echo "Restoring from backup..."
gunzip < "$BACKUP_FILE" | psql -h "${PGHOST:-db}" \
                                -p "${PGPORT:-5432}" \
                                -U "${PGUSER}" \
                                -d "${PGDATABASE}" \
                                -q

echo ""
echo "=========================================="
echo "Restore completed successfully!"
echo "=========================================="
echo "Next steps:"
echo "1. Restart HAPI FHIR: docker-compose restart hapi-fhir"
echo "2. HAPI FHIR will automatically reindex all resources"
echo "3. Check logs: docker-compose logs -f hapi-fhir"
echo ""
echo "Restore completed at $(date)"
