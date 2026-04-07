# FHIR SDC API

A Form Manager implementing the FHIR Structured Data Capture (SDC) specification for managing healthcare questionnaires, with custom operations on top of HAPI FHIR.

## Features

- **$package** - Bundle questionnaires with all dependencies (ValueSets, CodeSystems)
- **$localize** - Language-aware questionnaire retrieval
- **$populate** - Pre-fill questionnaires with patient data (via HAPI)
- **$extract** - Extract structured data from responses (via HAPI)

## Quick Start

```bash
# Clone repository
git clone <repo-url>
cd fhir-sdc-api

# Configure environment
cp .env.example .env

# Start services
docker compose up -d

# Verify (wait ~60s for HAPI to initialize)
curl http://localhost:8080/fhir/metadata | jq .fhirVersion
curl http://localhost:8000/health
```

## Architecture

```
                    ┌─────────────────┐
                    │   FastAPI       │ :8000
                    │   $package      │
                    │   $localize     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   HAPI FHIR     │ :8080
                    │   $populate     │
                    │   $extract      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   PostgreSQL    │ :5432
                    └─────────────────┘
```

## Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| FastAPI | 8000 | http://localhost:8000 | Custom SDC operations |
| HAPI FHIR | 8080 | http://localhost:8080/fhir | FHIR R4 server |
| PostgreSQL | 5432 | localhost:5432 | Database |

## API Endpoints

### Custom Operations (FastAPI)

```bash
# Package a Questionnaire with dependencies
GET http://localhost:8000/api/questionnaires/{id}/$package

# Localize a Questionnaire
GET http://localhost:8000/api/questionnaires/{id}/$localize?language=de

# Health check
GET http://localhost:8000/health
```

### Native FHIR Operations (HAPI)

```bash
# Search Questionnaires
GET http://localhost:8080/fhir/Questionnaire?status=active

# Populate a Questionnaire
POST http://localhost:8080/fhir/Questionnaire/{id}/$populate

# Extract from QuestionnaireResponse
POST http://localhost:8080/fhir/QuestionnaireResponse/$extract

# Expand ValueSet
GET http://localhost:8080/fhir/ValueSet/$expand?url=...
```

## Running Tests

```bash
# Start test environment (uses H2 in-memory database for speed)
docker compose -f docker-compose.test.yml up -d

# Run tests
cd api && pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Configuration

Environment variables (`.env`):

```bash
# PostgreSQL
POSTGRES_DB=hapi
POSTGRES_USER=admin
POSTGRES_PASSWORD=change-me-in-production

# HAPI FHIR
FHIR_VERSION=R4
HAPI_CORS_ALLOWED_ORIGIN=*

# FastAPI
FHIR_BASE_URL=http://hapi-fhir:8080/fhir
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=info
```

## Implementation Guides Installed

- **hl7.fhir.uv.sdc** v3.0.0 - SDC profiles and resources
- **de.medizininformatikinitiative.kerndatensatz.pro** v2026.0.0-ballot - MII PRO

## Project Structure

```
fhir-sdc-api/
├── api/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Settings
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic
│   ├── tests/                # Test suite
│   ├── Dockerfile
│   └── requirements.txt
├── hapi-config/              # HAPI configuration
├── hapi-scripts/             # Setup scripts
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Main environment
├── docker-compose.test.yml   # Test environment
└── docker-compose.aidbox.yml # Aidbox alternative
```

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design |
| [REQUIREMENTS.md](REQUIREMENTS.md) | Functional requirements |
| [SDC_FORM_MANAGER_REQUIREMENTS.md](SDC_FORM_MANAGER_REQUIREMENTS.md) | SDC conformance (136 items) |
| [TESTING.md](TESTING.md) | Test execution guide |
| [PRODUCTION_STATUS.md](PRODUCTION_STATUS.md) | What's implemented |
| [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) | Current limitations |

## Troubleshooting

### HAPI won't start
```bash
# Check PostgreSQL is ready
docker compose logs db

# HAPI takes 60-90s to initialize on first start
docker compose logs -f hapi-fhir
# Wait for: "Started Application in X seconds"
```

### Reset everything
```bash
docker compose down -v
docker compose up -d
```

## Alternative: Aidbox

To test against Aidbox instead of HAPI:

```bash
# Set license key
export AIDBOX_LICENSE="your-license"

# Start Aidbox environment
docker compose -f docker-compose.aidbox.yml up -d

# Aidbox available at http://localhost:8888
```

## License

[Your License Here]

## Related Projects

- [fhir-workshop-demo](https://github.com/your-org/fhir-workshop-demo) - Multi-site workshop demonstration
