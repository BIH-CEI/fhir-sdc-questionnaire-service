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
