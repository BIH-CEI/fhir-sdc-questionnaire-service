# Known Server Limitations and Test Expectations

This document tracks known limitations, expected failures, and server-specific behaviors in the SDC Form Manager test suite.

## PRO Library 0.1.1 — CQL execution gap

The PRO Library 0.1.1 ships a CQL scoring `Library` (`phq-9-scoring`) plus a `TestScript` that exercises `Library/$evaluate` for ten boundary/extreme PHQ-9 response fixtures (raw=0, 4, 5, 9, 10, 14, 15, 19, 20, 27 → expected TotalScore + Severity + PROMIS Depression T-Score). The CQL itself is **independently verified** — `cqframework/cql-translation-service` Docker image compiles it to ELM with 0 errors, 0 warnings (signatures=Overloads). The pre-compiled ELM JSON is shipped in `Library.content` alongside the raw CQL.

HAPI CR loads the Library at boot and the CQL engine kicks in on `Library/$evaluate` — but as of the version pinned in `Dockerfile.form-manager`, **the QuestionnaireResponse passed as a library parameter does not reach the CQL engine.** All three parameter-passing patterns tested (`resource`, `valueReference`, separate `data` Bundle) return `data-absent: unknown` for the scoring expressions. `QuestionnaireResponse/$extract` throws `NullPointerException: theResourceName must not be blank`.

This is a HAPI CR integration issue (not a CQL/spec issue). Two candidate paths for 0.1.2:

1. **Redesign the Library for SDC flow** — drop the `parameter "Response" QuestionnaireResponse` and use `context Patient` + `[QuestionnaireResponse]` retrieve. The Library then matches the SDC `$populate` / `sdc-calculatedExpression` evaluation flow rather than the direct-test flow.
2. **Pivot the runtime evaluator** — embed `cqf-fhir` engine (Java library) in the FastAPI sidecar, or call the `cql-translation-service` Docker as an evaluation endpoint. Bypasses HAPI CR for execution.

For 0.1.1 the Library + TestScript are shipped as **specification artefacts** — downstream consumers (Inferno, Touchstone, AEGIS) can run them against any conforming runtime even though our reference container doesn't yet execute them green.



## HAPI FHIR Server Limitations

### SDC Operations NOT Supported Natively

| Operation | Status | Our Implementation | Test Coverage |
|-----------|--------|-------------------|---------------|
| `$package` | ❌ Not in HAPI | ✅ Custom (PackageService) | 18 tests |
| `$populate` | ❌ Not in HAPI | ❌ Not implemented | 0 tests |
| `$extract` | ❌ Not in HAPI | ❌ Not implemented | 0 tests |
| `$assemble` | ❌ Not in HAPI | ❌ Not implemented | 0 tests |
| `$localize` | ❌ Not in HAPI | ✅ Custom (LocalizationService) | Future |

**Impact:** Our FastAPI application provides these operations by wrapping HAPI.

**Test Strategy:**
```python
@pytest.mark.xfail(
    reason="HAPI doesn't support $package natively",
    strict=True
)
async def test_hapi_does_not_support_package_natively(hapi_client):
    """Documents that we implement $package ourselves"""
    response = await hapi_client.get("/Questionnaire/123/$package")
    # Expected to fail with 404 or similar
```

### Validation Strictness

| Behavior | HAPI | Aidbox | Firely | Azure |
|----------|------|--------|--------|-------|
| Invalid enum values | ✅ Accepts | ❌ Rejects | ❌ Rejects | ❌ Rejects |
| Missing required fields | ⚠️ Sometimes accepts | ❌ Rejects | ❌ Rejects | ❌ Rejects |
| Profile validation | ⚠️ Lenient | ✅ Strict | ✅ Strict | ✅ Strict |

**Server Profile:**
```python
SERVER_PROFILES = {
    "hapi": {
        "validation_strict": False,  # HAPI is lenient
    },
    "aidbox": {
        "validation_strict": True,   # Aidbox validates strictly
    },
}
```

**Test Example:**
```python
async def test_invalid_enum_value(api_client, server_profile):
    """Test validation of invalid enum values"""
    questionnaire = {
        "resourceType": "Questionnaire",
        "status": "INVALID_VALUE"  # Not in ValueSet
    }

    response = await api_client.post("/api/questionnaires/", json=questionnaire)

    if server_profile["validation_strict"]:
        assert response.status_code == 422, "Strict servers reject invalid enums"
    else:
        # HAPI might accept this
        assert response.status_code in [200, 201, 422]
```

### GraphQL Support

| Server | GraphQL Support |
|--------|----------------|
| HAPI FHIR | ❌ No |
| Aidbox | ✅ Yes |
| Firely | ❌ No |
| Azure | ❌ No |

**Test Example:**
```python
@pytest.mark.skipif(
    not server_profile.get("supports_graphql"),
    reason="Server doesn't support GraphQL"
)
async def test_graphql_query(fhir_server, server_profile):
    """Test GraphQL queries (Aidbox only)"""
    query = """
    {
      QuestionnaireList {
        id
        status
      }
    }
    """
    # Only runs on Aidbox
```

## Expected Test Failures

### Tests Marked with `@pytest.mark.xfail`

| Test | Reason | Expected Result |
|------|--------|----------------|
| `test_hapi_does_not_support_package_natively` | HAPI doesn't support $package | XFAIL (404/400/501) |
| (Future) `test_hapi_strict_validation` | HAPI is lenient | XFAIL (accepts invalid data) |

**Understanding xfail:**
- `strict=True` - Test MUST fail, or mark as FAILED
- `strict=False` - Test may pass or fail, both are acceptable

### Tests Marked with `@pytest.mark.skipif`

| Test | Condition | Reason |
|------|-----------|--------|
| (Future) `test_graphql_queries` | `not supports_graphql` | Server doesn't support feature |
| (Future) `test_xml_content_type` | `not supports_xml` | Server doesn't support XML |

## Server Comparison Matrix

### Feature Support

| Feature | HAPI | Aidbox | Firely | Azure |
|---------|------|--------|--------|-------|
| FHIR R4 | ✅ | ✅ | ✅ | ✅ |
| JSON | ✅ | ✅ | ✅ | ✅ |
| XML | ✅ | ✅ | ✅ | ✅ |
| GraphQL | ❌ | ✅ | ❌ | ❌ |
| OAuth2 | ✅ | ✅ | ✅ | ✅ |
| SMART on FHIR | ✅ | ✅ | ✅ | ✅ |
| Strict Validation | ❌ | ✅ | ✅ | ✅ |
| $package (native) | ❌ | ❌ | ❌ | ❌ |

### Performance Characteristics

| Metric | HAPI | Aidbox | Firely | Azure |
|--------|------|--------|--------|-------|
| Read latency (p95) | ~50ms | ~30ms | ~40ms | ~100ms* |
| Search latency (p95) | ~150ms | ~80ms | ~120ms | ~200ms* |
| Throughput | Medium | High | High | High |
| Startup time | ~120s | ~60s | ~60s | N/A (cloud) |

*Azure latency includes network overhead

## Test Execution Recommendations

### For Local Development (HAPI)

```bash
# Default - runs against HAPI
cd api
pytest tests/ -v

# Expect some lenient validation behavior
# Our custom $package implementation should work
```

### For Strict Validation Testing (Aidbox/Firely)

```bash
# Start Aidbox
docker-compose -f docker-compose.aidbox.yml up -d

# Run tests
pytest tests/ --fhir-server=aidbox -v

# Expect stricter validation failures
```

### For CI/CD (Multi-Server)

```yaml
# .github/workflows/test.yml
strategy:
  matrix:
    fhir-server: [hapi, aidbox]

steps:
  - name: Test against ${{ matrix.fhir-server }}
    run: pytest tests/ --fhir-server=${{ matrix.fhir-server }} -v
```

## Known Issues & Workarounds

### Issue 1: HAPI Accepts Invalid Questionnaire.status

**Problem:**
```python
questionnaire = {
    "resourceType": "Questionnaire",
    "status": "INVALID"  # Should be: draft, active, retired, unknown
}
# HAPI accepts this ❌
```

**Workaround:**
```python
# Add explicit validation in FastAPI layer
from pydantic import validator

class QuestionnaireCreate(BaseModel):
    status: Literal["draft", "active", "retired", "unknown"]
```

**Test Coverage:**
```python
# Test documents this limitation
async def test_invalid_status_value(api_client, server_profile):
    if not server_profile["validation_strict"]:
        pytest.skip("HAPI allows invalid status values")
    # Test strict validation
```

### Issue 2: HAPI Metadata Endpoint Differences

**Problem:**
```python
# Some HAPI versions return different CapabilityStatement structure
capability = await hapi_client.get("/metadata")
# May not include all expected fields
```

**Workaround:**
```python
# Test with optional assertions
assert "fhirVersion" in capability
if capability.get("software"):
    assert capability["software"].get("name")  # Optional field
```

### Issue 3: Search Parameter Support Varies

**Problem:**
```python
# Not all search parameters work on all servers
response = await fhir_server.get("/Questionnaire?_lastUpdated=gt2024-01-01")
# HAPI: ✅ Works
# Some servers: ❌ May not support comparators
```

**Workaround:**
```python
@pytest.mark.parametrize("comparator", ["gt", "lt", "ge", "le"])
async def test_date_comparators(fhir_server, server_profile, comparator):
    if not server_profile.get("supports_date_comparators", True):
        pytest.skip("Server doesn't support date comparators")
    # Test date search
```

## Adding New Server Limitations

### Step 1: Update SERVER_PROFILES

```python
# api/tests/conftest.py
SERVER_PROFILES = {
    "new-server": {
        "name": "New Server",
        "base_url": "http://localhost:9000",
        "validation_strict": True,
        "supports_xml": False,  # Known limitation
        "supports_graphql": False,
        "known_issues": [
            "Doesn't support _sort parameter",
            "No $expand on ValueSet",
        ],
    },
}
```

### Step 2: Add Test with xfail or skipif

```python
@pytest.mark.skipif(
    server_profile.get("name") == "New Server",
    reason="New Server doesn't support _sort parameter"
)
async def test_search_with_sort(fhir_server, server_profile):
    """Test _sort search parameter"""
    response = await fhir_server.get("/Questionnaire?_sort=-date")
    assert response.status_code == 200
```

### Step 3: Document in This File

Add entry to the appropriate section above.

## Resources

- [HAPI FHIR Documentation](https://hapifhir.io/hapi-fhir/docs/)
- [Aidbox Documentation](https://docs.aidbox.app/)
- [Firely Server Documentation](https://docs.fire.ly/projects/Firely-Server/)
- [Azure Health Data Services](https://learn.microsoft.com/en-us/azure/healthcare-apis/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [SDC Implementation Guide](https://build.fhir.org/ig/HL7/sdc/)

## Updating This Document

When you discover a new server limitation:

1. Add it to the appropriate section
2. Create a test with `@pytest.mark.xfail` or `@pytest.mark.skipif`
3. Update the comparison matrix
4. Document the workaround
5. Update `SERVER_PROFILES` in `conftest.py`

---

**Last Updated:** 2025-10-26
**Maintainer:** Development Team
