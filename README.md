# FHIR SDC Form Manager

A Form Manager implementing the FHIR Structured Data Capture (SDC) specification for managing healthcare questionnaires, value sets, and code systems.

## Architecture

- **HAPI FHIR Server** - FHIR R4 compliant server with terminology services
- **PostgreSQL** - Primary database for FHIR resources
- **FastAPI** - Custom business logic layer for SDC operations
- **React** (future) - Web UI for form management

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Setup

1. Clone the repository:
```bash
git clone <your-repo>
cd form_server
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env and update passwords for production!
```

3. Start services:
```bash
docker-compose up -d
```

4. Verify services:
```bash
# Check HAPI FHIR
curl http://localhost:8080/fhir/metadata

# Check FastAPI
curl http://localhost:8000/health
```

## Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| HAPI FHIR | 8080 | http://localhost:8080/fhir | FHIR R4 server |
| FastAPI | 8000 | http://localhost:8000 | Custom API |
| PostgreSQL | 5432 | localhost:5432 | Database |

## API Endpoints

### HAPI FHIR (Direct FHIR Operations)

```bash
# Search Questionnaires
GET http://localhost:8080/fhir/Questionnaire?status=active

# Create Questionnaire
POST http://localhost:8080/fhir/Questionnaire
Content-Type: application/fhir+json
{ "resourceType": "Questionnaire", ... }

# Expand ValueSet
GET http://localhost:8080/fhir/ValueSet/$expand?url=http://example.org/ValueSet/example
```

### FastAPI (Custom Operations)

```bash
# Enhanced search with autocomplete
GET http://localhost:8000/api/questionnaires/search?q=diabetes

# Package Questionnaire with dependencies
GET http://localhost:8000/api/questionnaires/{id}/$package

# Health check
GET http://localhost:8000/health
```

## Backup & Restore

### Manual Backup

```bash
# Create backup
docker-compose exec -T db pg_dump -U admin hapi | gzip > backups/manual_backup.sql.gz
```

### Automated Backups

```bash
# Start with automated daily backups (2 AM)
docker-compose -f docker-compose.yml -f docker-compose.backup.yml up -d

# Manual backup trigger
docker-compose exec backup /scripts/backup.sh
```

Backups are stored in `./backups/` and retained for 7 days by default.

### Restore from Backup

```bash
# Stop HAPI FHIR to prevent conflicts
docker-compose stop hapi-fhir

# Restore database
docker-compose exec backup /scripts/restore.sh /backups/fhir_backup_20251010_020000.sql.gz

# Restart HAPI FHIR (will automatically reindex)
docker-compose start hapi-fhir

# Monitor reindexing
docker-compose logs -f hapi-fhir
```

## Development

### Project Structure

```
form_server/
├── api/                    # FastAPI application
│   ├── app/
│   │   ├── main.py        # FastAPI entry point
│   │   ├── config.py      # Configuration
│   │   ├── routers/       # API endpoints
│   │   ├── services/      # Business logic
│   │   └── models/        # Pydantic models
│   ├── Dockerfile
│   └── requirements.txt
├── scripts/               # Backup/restore scripts
│   ├── backup.sh
│   └── restore.sh
├── backups/               # Database backups (git-ignored)
├── docker-compose.yml     # Main services
├── docker-compose.backup.yml  # Optional backup service
├── .env                   # Environment variables (git-ignored)
├── .env.example           # Environment template
└── REQUIREMENTS.md        # Detailed requirements

```

### Running Tests

```bash
# Run FastAPI tests (when implemented)
docker-compose exec fastapi pytest

# Test FHIR connectivity
curl http://localhost:8080/fhir/metadata | jq '.fhirVersion'
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f hapi-fhir
docker-compose logs -f fastapi
docker-compose logs -f db
```

## Configuration

Environment variables in `.env`:

```bash
# PostgreSQL
POSTGRES_DB=hapi
POSTGRES_USER=admin
POSTGRES_PASSWORD=change-me-in-production

# HAPI FHIR
FHIR_VERSION=R4
HAPI_CORS_ALLOWED_ORIGIN=*
HAPI_DEFAULT_PAGE_SIZE=20
HAPI_MAX_PAGE_SIZE=200

# FastAPI
FHIR_BASE_URL=http://hapi-fhir:8080/fhir
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info
```

## Deployment

See deployment guides in `docs/deployment/`:
- [DigitalOcean Deployment](docs/deployment/digitalocean.md)
- [AWS Deployment](docs/deployment/aws.md)
- [Security Best Practices](docs/deployment/security.md)

## SDC Capabilities

This Form Manager implements the following SDC capabilities based on the [SDC Form Manager Capability Statement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html):

### Core Resources (SHALL Support)
- **Questionnaire** - Read, Create, Update, Delete
- **ValueSet** - Read, Create, Update, Delete, $expand, $validate-code
- **CodeSystem** - Read, Create, Update, Delete, $lookup
- **Library** - Read, Create, Update, Delete

### SDC Operations (with CQL enabled)
- ✅ `Questionnaire/$populate` - Pre-fill questionnaires with patient data
- ✅ `QuestionnaireResponse/$extract` - Extract structured data from responses
- ✅ `Questionnaire/$package` - Generate bundle with dependencies
- ⚠️ `Questionnaire/$assemble` - Assemble modular questionnaires (requires custom implementation)

### Implementation Guides Installed
- **hl7.fhir.uv.sdc** v3.0.0 - SDC profiles and resources
- **de.medizininformatikinitiative.kerndatensatz.pro** v2026.0.0-ballot - MII PRO

### Configuration Documentation
- **[SDC_CONFIGURATION.md](SDC_CONFIGURATION.md)** - How we enabled SDC support (CQL + SDC IG)
- **[IMPLEMENTING_ASSEMBLE_OPERATION.md](IMPLEMENTING_ASSEMBLE_OPERATION.md)** - Detailed guide for implementing $assemble
- **[ASSEMBLE_OPERATION_SUMMARY.md](ASSEMBLE_OPERATION_SUMMARY.md)** - Quick reference for $assemble implementation options

## Troubleshooting

### HAPI FHIR won't start

```bash
# Check if PostgreSQL is ready
docker-compose logs db

# Wait for database initialization
docker-compose up -d db
# Wait 30 seconds
docker-compose up -d hapi-fhir
```

### Connection refused errors

```bash
# Verify all services are running
docker-compose ps

# Check network connectivity
docker-compose exec fastapi ping hapi-fhir
docker-compose exec fastapi ping db
```

### Reset everything

```bash
# Stop and remove all containers, volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Your License Here]

## References

- [FHIR SDC Specification](https://build.fhir.org/ig/HL7/sdc/)
- [HAPI FHIR Documentation](https://hapifhir.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
