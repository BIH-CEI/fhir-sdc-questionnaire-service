# SDC Form Manager Architecture

## Overview

This project implements a **custom SDC-compliant Form Manager** that wraps HAPI FHIR to provide SDC-specific operations that HAPI doesn't natively support.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                   Client / Tests                     │
└───────────────────┬─────────────────────────────────┘
                    │
                    v
┌─────────────────────────────────────────────────────┐
│            FastAPI Application (Port 8001)           │
│  ┌─────────────────────────────────────────────┐   │
│  │  SDC Operations (Custom Implementation)      │   │
│  │  - $package (PackageService)                │   │
│  │  - $localize (LocalizationService)          │   │
│  │  - Questionnaire CRUD with validation       │   │
│  └──────────────┬──────────────────────────────┘   │
└─────────────────┼──────────────────────────────────┘
                  │
                  │ HTTP/FHIR API calls
                  v
┌─────────────────────────────────────────────────────┐
│         HAPI FHIR Server (Port 8081/fhir)            │
│  ┌─────────────────────────────────────────────┐   │
│  │  Standard FHIR Operations                    │   │
│  │  - CRUD (Create, Read, Update, Delete)       │   │
│  │  - Search                                    │   │
│  │  - Basic validation                          │   │
│  │  - Resource storage                          │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
           │
           v
    ┌──────────────┐
    │   Database   │
    │  (H2/MySQL)  │
    └──────────────┘
```

## Component Responsibilities

### FastAPI Application (`api/app/`)

**Purpose:** Provide SDC-compliant Form Manager capabilities

**Key Components:**
- **`routers/questionnaires.py`** - REST endpoints for SDC operations
- **`services/package_service.py`** - Implements $package operation
  - Resolves transitive dependencies (ValueSet → CodeSystem chains)
  - Assembles Bundle with all required resources
  - Handles circular dependencies
- **`services/localization_service.py`** - Implements $localize operation
  - Language translation
  - Locale-specific rendering
- **`services/fhir_client.py`** - HAPI communication layer

**Custom Operations (Not in HAPI):**
- ✅ `GET /api/questionnaires/{id}/$package`
- ✅ `POST /api/questionnaires/$package`
- ✅ `GET /api/questionnaires/$package?url={canonical}`
- ✅ `POST /api/questionnaires/{id}/$localize`

### HAPI FHIR Server

**Purpose:** FHIR-compliant data storage and basic operations

**Provides:**
- ✅ Resource storage (Questionnaire, ValueSet, CodeSystem, Library)
- ✅ CRUD operations
- ✅ Search parameters
- ✅ Basic FHIR validation
- ✅ CapabilityStatement

**Does NOT Provide (as of HAPI v6.x):**
- ❌ SDC $package operation
- ❌ SDC $populate operation
- ❌ SDC $extract operation
- ❌ Custom $localize operation

## What the Tests Validate

### Integration Tests (`api/tests/integration/`)

Test the **FastAPI application** endpoints:

```python
async def test_create_questionnaire(api_client):
    # Tests: POST /api/questionnaires/
    # Validates: FastAPI → HAPI communication
    response = await api_client.post("/api/questionnaires/", json=questionnaire)
```

**Fixture:** `api_client` → `http://localhost:8001`

### SDC Compliance Tests (`api/tests/sdc_compliance/`)

Test **custom SDC operations** implemented in FastAPI:

```python
async def test_package_operation(api_client, load_test_fixtures):
    # Tests: GET /api/questionnaires/{id}/$package
    # Validates: Custom PackageService implementation
    response = await api_client.get(f"/api/questionnaires/{id}/$package")
```

**Fixture:** `api_client` → `http://localhost:8001`

**What's being tested:**
- ✅ Our PackageService correctly queries HAPI for resources
- ✅ Dependency resolution works (ValueSet → CodeSystem chains)
- ✅ Bundle assembly follows SDC spec
- ✅ Error handling for missing dependencies

**What's NOT being tested:**
- ❌ HAPI's native $package support (it doesn't have it)
- ❌ Other FHIR servers' $package implementations

### HAPI Direct Tests

Tests that interact **directly with HAPI** (bypassing FastAPI):

```python
async def test_hapi_search(hapi_client):
    # Tests: GET http://localhost:8081/fhir/Questionnaire?status=active
    # Validates: HAPI's search capabilities
    response = await hapi_client.get("/Questionnaire?status=active")
```

**Fixture:** `hapi_client` → `http://localhost:8081/fhir`

### Known HAPI Limitations (Documented with xfail)

```python
@pytest.mark.xfail(
    reason="HAPI FHIR does not natively support $package operation",
    strict=True
)
async def test_hapi_does_not_support_package_natively(hapi_client):
    """
    This test documents that HAPI doesn't support $package.
    Expected to fail - that's why we built our own implementation!
    """
    response = await hapi_client.get(f"/Questionnaire/{id}/$package")
    # This will fail (404 or similar) - and that's expected!
```

## Multi-Server Support

The test suite supports testing against different FHIR servers:

```bash
# Test against HAPI (default)
pytest tests/ --fhir-server=hapi -v

# Test against Aidbox
pytest tests/ --fhir-server=aidbox -v

# Custom server
pytest tests/ --fhir-url=http://custom-server:8080/fhir -v
```

**What changes:**
- `hapi_client` / `fhir_server` fixture points to different server
- FastAPI still implements $package (server-agnostic)
- Tests validate our implementation works with different backends

## Key Design Decisions

### Why Wrap HAPI?

1. **HAPI doesn't support SDC operations natively**
   - No $package, $populate, $extract operations
   - We need these for SDC compliance

2. **Custom business logic**
   - Dependency resolution with circular reference handling
   - Localization support
   - Enhanced validation

3. **Server-agnostic architecture**
   - Can swap HAPI for Aidbox, Firely, Azure FHIR
   - Our SDC logic stays the same

### Why Not Extend HAPI Directly?

1. **Separation of concerns** - FHIR storage vs. SDC operations
2. **Easier testing** - Mock FHIR client, test SDC logic independently
3. **Language choice** - Python FastAPI vs Java HAPI
4. **Deployment flexibility** - Can scale FastAPI and HAPI independently

### Docker Compose Architecture Decisions

#### Test vs Production Environments

We maintain two separate Docker Compose configurations:

1. **Production (`docker-compose.yml`)**
   - PostgreSQL + HAPI FHIR + FastAPI
   - Persistent volumes for data storage
   - HAPI uses PostgreSQL database
   - Ports: 8080 (HAPI), 8000 (FastAPI), 5432 (PostgreSQL)
   - Network name: `fhir-network`
   - Use case: Development and production deployment

2. **Test (`docker-compose.test.yml`)**
   - HAPI FHIR + FastAPI only (no PostgreSQL)
   - HAPI uses in-memory H2 database
   - Ports: 8081 (HAPI), 8001 (FastAPI)
   - Network name: `fhir-sdc-test-network`
   - Use case: CI/CD and local testing

**Rationale:**
- Test environment needs to be fast (H2 in-memory) and isolated
- Production needs data persistence (PostgreSQL with volumes)
- Different ports prevent conflicts when running both simultaneously
- Separate networks ensure complete isolation

#### Healthcheck Strategy

**Production Environment:**
- PostgreSQL: Has healthcheck using `pg_isready`
- FastAPI: Has healthcheck using `curl http://localhost:8000/health`
- HAPI: No healthcheck (container doesn't include curl/wget/ls)
- **Solution**: Use `depends_on` with service_healthy condition for PostgreSQL, and 30-second sleep delay for HAPI startup

**Test Environment:**
- HAPI: No healthcheck
- FastAPI: No explicit healthcheck in compose file
- **Solution**: Tests wait for servers using retry logic in conftest.py fixtures

**Rationale:**
- HAPI container lacks shell utilities for healthchecks
- Adding healthcheck dependencies would require custom HAPI image
- Sleep delays + application-level retries are simpler and sufficient
- Tests are responsible for verifying server readiness (better error messages)

#### Environment Variable Configuration

**Test Environment (`docker-compose.test.yml`):**
```yaml
environment:
  FHIR_BASE_URL: http://hapi-fhir-test:8080/fhir  # Docker network name
  API_BASE_URL: http://localhost:8000              # For external access
```

**Test Configuration (`conftest.py`):**
```python
SERVER_PROFILES = {
    "hapi": {
        "base_url": os.getenv("FHIR_BASE_URL", "http://localhost:8081/fhir"),
        # ...
    }
}
```

**Rationale:**
- Tests running inside Docker containers use Docker network names (e.g., `hapi-fhir-test`)
- Tests running on host use `localhost` with mapped ports
- Environment variables allow flexibility without code changes
- `os.getenv()` in conftest.py enables environment-based configuration

#### Docker Networking

**Key Decision**: Use Docker network names for inter-container communication

**Example:**
- FastAPI container accesses HAPI at: `http://hapi-fhir-test:8080/fhir`
- Host machine accesses HAPI at: `http://localhost:8081/fhir`

**Rationale:**
- Docker's internal DNS resolves service names to container IPs
- Avoids port mapping issues and network conflicts
- More reliable than localhost (which can fail in Docker-in-Docker scenarios)
- Follows Docker Compose best practices

#### Volume Management and Cleanup

**Production Volumes:**
- `postgres_data`: PostgreSQL database files
- `hapi_data`: HAPI configuration and work files

**Test Volumes:**
- None (ephemeral containers)
- Test data deleted on container removal

**Cleanup Strategy:**
```bash
# Clean test environment (safe, no data loss)
docker-compose -f docker-compose.test.yml down -v

# Clean production (DESTROYS DATA - use carefully)
docker-compose down -v
```

**Rationale:**
- Test isolation requires clean state between runs
- Production data persistence requires named volumes
- Explicit volume flags prevent accidental data loss
- Test fixtures handle resource cleanup programmatically

#### Test Isolation Strategy

**Per-Test Resource Cleanup:**
- Fixtures like `clean_questionnaire`, `clean_valueset`, `clean_codesystem`
- Track created resource IDs and delete in teardown
- Each test gets isolated resources

**Optional Full Cleanup:**
- `cleanup_all_resources` fixture (not run by default)
- Deletes ALL test resources across resource types
- Use explicitly when test needs completely clean database

**Rationale:**
- Per-test cleanup prevents test interference
- Optional full cleanup handles edge cases
- Balance between isolation and test speed
- Supports both parallel and sequential test execution

#### HAPI Configuration

**Test HAPI (`docker-compose.test.yml`):**
```yaml
environment:
  hapi.fhir.validation.requests_enabled: true
  hapi.fhir.enable_repository_validating_interceptor: true
  spring.datasource.url: jdbc:h2:mem:testdb
```

**Production HAPI (`docker-compose.yml`):**
```yaml
environment:
  hapi.fhir.cql_enabled: true
  hapi.fhir.validation_enabled: true
  spring.datasource.url: jdbc:postgresql://db:5432/${POSTGRES_DB}
```

**Rationale:**
- Test HAPI prioritizes speed (H2 in-memory) over features
- Production HAPI enables full SDC capabilities (CQL for $populate/$extract)
- Both validate requests to catch FHIR compliance issues early
- Configuration via environment variables allows easy tuning without rebuilding images

## Data Flow Example: $package Operation

```
1. Client calls: GET /api/questionnaires/123/$package

2. FastAPI receives request
   └─> routers/questionnaires.py::package_questionnaire_by_id()

3. PackageService.create_package()
   ├─> Fetch Questionnaire from HAPI
   │   └─> GET http://localhost:8081/fhir/Questionnaire/123
   │
   ├─> Extract answerValueSet references
   │   └─> ["http://example.org/ValueSet/vs1", ...]
   │
   ├─> Fetch each ValueSet from HAPI
   │   └─> GET http://localhost:8081/fhir/ValueSet?url=http://example.org/ValueSet/vs1
   │
   ├─> Extract CodeSystem references from ValueSets
   │   └─> ["http://example.org/CodeSystem/cs1", ...]
   │
   ├─> Fetch each CodeSystem from HAPI
   │   └─> GET http://localhost:8081/fhir/CodeSystem?url=http://example.org/CodeSystem/cs1
   │
   └─> Assemble Bundle
       └─> {
             "resourceType": "Bundle",
             "type": "collection",
             "entry": [
               {"resource": {Questionnaire}},
               {"resource": {ValueSet1}},
               {"resource": {CodeSystem1}},
               ...
             ]
           }

4. Return Bundle to client
```

## Testing Strategy

### 1. Unit Tests (Future)
- Test PackageService in isolation with mocked FHIR client
- Test dependency resolution logic
- Test error handling

### 2. Integration Tests (Current)
- Test FastAPI endpoints with real HAPI backend
- Validate request/response formats
- Test error scenarios

### 3. SDC Compliance Tests (Current)
- Test against SDC IG requirements
- Document requirement IDs in test docstrings
- Track coverage (80% SHALL, 34% total)

### 4. Multi-Server Tests (Supported)
- Run same tests against HAPI, Aidbox, Firely
- Use `server_profile` fixture for server-specific logic
- Document known server differences with `@pytest.mark.xfail`

## Environment Configuration

```bash
# Docker Compose Setup
docker-compose up -d           # Start HAPI + FastAPI

# Test Configuration
FHIR_BASE_URL=http://localhost:8081/fhir   # HAPI server
API_BASE_URL=http://localhost:8001         # FastAPI server

# Runtime Configuration
python api/app/main.py                      # Start FastAPI
# HAPI runs on http://localhost:8081/fhir
# FastAPI runs on http://localhost:8001
```

## Summary

| Component | Role | Port | Implements SDC? |
|-----------|------|------|-----------------|
| FastAPI | SDC Operations | 8001 | ✅ Yes ($package, $localize) |
| HAPI FHIR | Storage & CRUD | 8081 | ❌ No (just storage) |
| Tests | Validation | N/A | Validates FastAPI's SDC implementation |

**Bottom Line:**
- **HAPI = Storage backend** (like a database)
- **FastAPI = SDC Form Manager** (implements spec)
- **Tests validate FastAPI**, not HAPI's SDC support
- We **wrap** HAPI to add missing SDC functionality
