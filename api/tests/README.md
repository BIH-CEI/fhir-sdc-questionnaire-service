# Test Suite Documentation

## Overview

This test suite provides comprehensive testing for the FHIR SDC Form Manager API, including:

1. **SDC Compliance Tests** - Validates SDC Form Manager specification compliance
2. **Integration Tests** - Tests API endpoints with real HAPI FHIR server
3. **Failure Scenario Tests** - Tests error handling and edge cases

---

## Test Structure

```
tests/
├── conftest.py                       # Shared pytest fixtures
├── fixtures/
│   └── sample_resources.py           # FHIR test data (PHQ-2, Diabetes, etc.)
├── sdc_compliance/
│   └── test_package_operation.py     # SDC $package operation tests
└── integration/
    └── test_questionnaire_crud.py    # CRUD operation tests
```

---

## Running Tests

### Prerequisites

1. **Install test dependencies:**
   ```bash
   cd api
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```

2. **Start test environment:**
   ```bash
   docker-compose -f docker-compose.test.yml up -d
   ```

   This starts:
   - HAPI FHIR test server on `localhost:8081`
   - FastAPI test server on `localhost:8001`

3. **Wait for services to be ready** (handled automatically in fixtures)

---

### Test Execution Commands

#### Run All Tests
```bash
pytest tests/ -v
```

#### Run SDC Compliance Tests Only
```bash
pytest tests/sdc_compliance/ -v
```

#### Run Integration Tests Only
```bash
pytest tests/integration/ -v
```

#### Run with Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

#### Run Specific Test File
```bash
pytest tests/sdc_compliance/test_package_operation.py -v
```

#### Run Tests by Marker
```bash
# SDC compliance tests only
pytest -m sdc_compliance -v

# Integration tests only
pytest -m integration -v

# Failure scenario tests only
pytest -m failure_scenarios -v
```

#### Run with Detailed Output
```bash
pytest tests/ -v --tb=short --capture=no
```

---

## Test Markers

Tests are organized using pytest markers:

| Marker | Description | Example |
|--------|-------------|---------|
| `sdc_compliance` | SDC specification compliance tests | `@pytest.mark.sdc_compliance` |
| `integration` | Tests requiring HAPI FHIR | `@pytest.mark.integration` |
| `failure_scenarios` | Error handling and edge cases | `@pytest.mark.failure_scenarios` |
| `slow` | Slow-running tests | `@pytest.mark.slow` |

---

## Test Categories

### 1. SDC Compliance Tests

**Purpose:** Validate compliance with SDC Form Manager CapabilityStatement

**Location:** `tests/sdc_compliance/test_package_operation.py`

**Key Test Cases:**

| Test | SDC Requirement | Reference |
|------|----------------|-----------|
| `test_package_returns_collection_bundle` | Bundle type='collection' | SDC IG 3.2.1 |
| `test_questionnaire_is_first_entry` | Questionnaire first in bundle | SDC IG Best Practices |
| `test_includes_referenced_valuesets` | Include all ValueSets | SDC IG 3.2.1 |
| `test_includes_referenced_codesystems` | Transitive dependencies | SDC IG 3.2.1 |
| `test_missing_dependency_returns_operation_outcome` | Warning for missing deps | SDC IG 3.2.1 |
| `test_supports_include_dependencies_parameter` | Parameter support | OperationDefinition |
| `test_instance_level_endpoint` | GET /Questionnaire/{id}/$package | OperationDefinition |
| `test_type_level_post_endpoint` | POST /Questionnaire/$package | OperationDefinition |
| `test_canonical_url_resolution` | Canonical URL + version | FHIR R4 Canonical |

**Example Run:**
```bash
pytest tests/sdc_compliance/ -v --tb=short
```

**Expected Output:**
```
tests/sdc_compliance/test_package_operation.py::TestSDCPackageOperationCompliance::test_package_returns_collection_bundle PASSED
tests/sdc_compliance/test_package_operation.py::TestSDCPackageOperationCompliance::test_questionnaire_is_first_entry PASSED
...
==================== 18 passed in 45.23s ====================
```

---

### 2. Integration Tests

**Purpose:** Test FastAPI proxy to HAPI FHIR with real server

**Location:** `tests/integration/test_questionnaire_crud.py`

**Test Classes:**

#### `TestQuestionnaireCreate`
- `test_create_questionnaire_success` - Create valid Questionnaire
- `test_create_questionnaire_invalid_type_returns_400` - Wrong resourceType
- `test_create_questionnaire_missing_required_field` - HAPI validation

#### `TestQuestionnaireRead`
- `test_get_questionnaire_success` - Retrieve by ID
- `test_get_questionnaire_not_found_returns_404` - Missing resource

#### `TestQuestionnaireUpdate`
- `test_update_questionnaire_success` - Update existing resource
- `test_update_questionnaire_not_found_returns_404` - Invalid ID
- `test_update_questionnaire_id_mismatch_returns_400` - ID conflict

#### `TestQuestionnaireDelete`
- `test_delete_questionnaire_success` - Delete resource
- `test_delete_questionnaire_not_found_returns_404` - Invalid ID

#### `TestQuestionnaireSearch`
- `test_search_questionnaires_by_status` - Filter by status
- `test_search_questionnaires_by_title` - Search by title
- `test_search_questionnaires_with_count_limit` - Pagination
- `test_search_questionnaires_no_results` - Empty results

#### `TestHAPIFailureScenarios`
- `test_malformed_json_returns_400` - Invalid JSON handling
- `test_large_payload_handling` - Large resource handling
- `test_concurrent_updates_handling` - Concurrent modification

**Example Run:**
```bash
pytest tests/integration/ -v
```

---

### 3. Failure Scenario Tests

**Purpose:** Test error handling and edge cases

**Key Scenarios:**

| Scenario | Expected Behavior | Status Code |
|----------|-------------------|-------------|
| HAPI unreachable | Graceful error | 500 |
| Invalid JSON | Validation error | 422 |
| Missing resource | Not found | 404 |
| Invalid resource type | Bad request | 400 |
| Concurrent updates | Handle versioning | 200/409 |
| Large payload | Accept or reject | 200/413 |
| Network timeout | Timeout error | 500 |

**Example Run:**
```bash
pytest -m failure_scenarios -v
```

---

## Fixtures

### Session-Scoped Fixtures

**`hapi_client`** - Async HAPI FHIR client
- Waits for HAPI to be ready
- Base URL: `http://localhost:8081/fhir`
- Timeout: 30 seconds

**`api_client`** - Async FastAPI client
- Waits for API to be ready
- Base URL: `http://localhost:8001`

**`load_test_fixtures`** - Loads common test data
- PHQ-2 Questionnaire, ValueSet, CodeSystem
- Diabetes Questionnaire, ValueSet
- Returns dict of resource IDs

### Function-Scoped Fixtures

**`clean_questionnaire`** - Create and auto-cleanup Questionnaire
```python
async def test_example(clean_questionnaire):
    q_id = await clean_questionnaire({"resourceType": "Questionnaire", ...})
    # Test code...
    # Automatic cleanup after test
```

**`clean_valueset`** - Create and auto-cleanup ValueSet

**`clean_codesystem`** - Create and auto-cleanup CodeSystem

---

## Test Data

### Sample Resources

Located in `tests/fixtures/sample_resources.py`:

| Resource | Description | Dependencies |
|----------|-------------|--------------|
| `PHQ2_QUESTIONNAIRE` | PHQ-2 Depression Screening | 1 ValueSet |
| `PHQ2_VALUESET` | PHQ-2 frequency answers | 1 CodeSystem |
| `PHQ2_CODESYSTEM` | PHQ frequency codes | None |
| `DIABETES_QUESTIONNAIRE` | Diabetes risk assessment | 1 ValueSet |
| `GLUCOSE_VALUESET` | Glucose level ranges | LOINC (external) |
| `SIMPLE_TEXT_QUESTIONNAIRE` | Text-only questions | None |
| `QUESTIONNAIRE_WITH_LIBRARY` | With CQL library | 1 Library |
| `COMPLEX_NESTED_QUESTIONNAIRE` | Nested item groups | 1 ValueSet |

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/test.yml`

**Triggers:**
- Push to `master`, `main`, `develop`
- Pull requests to these branches

**Steps:**
1. Checkout code
2. Set up Python 3.11
3. Install dependencies (with caching)
4. Start HAPI FHIR test server
5. Wait for HAPI to be healthy
6. Start FastAPI test server
7. Run SDC compliance tests
8. Run integration tests
9. Generate coverage report
10. Upload coverage to Codecov
11. Archive test artifacts
12. Tear down environment

**Manual Run:**
```bash
# From project root
.github/workflows/test.yml  # Uses docker-compose.test.yml
```

---

## Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Package Service | 90% | TBD |
| Dependency Resolver | 95% | TBD |
| API Endpoints | 80% | TBD |
| Overall | 85% | TBD |

**Generate Coverage Report:**
```bash
pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## Troubleshooting

### HAPI FHIR Not Starting

**Symptom:** Tests fail with "HAPI FHIR not ready after 120 seconds"

**Solutions:**
1. Check Docker is running: `docker ps`
2. View HAPI logs: `docker logs hapi-fhir-test`
3. Restart containers: `docker-compose -f docker-compose.test.yml restart`
4. Increase timeout in `conftest.py` (line 32)

### Tests Hanging

**Symptom:** Tests start but never complete

**Solutions:**
1. Check FastAPI is running: `curl http://localhost:8001/health`
2. Check HAPI is running: `curl http://localhost:8081/fhir/metadata`
3. View logs: `docker-compose -f docker-compose.test.yml logs`

### Fixture Cleanup Issues

**Symptom:** Test fails due to existing resources

**Solutions:**
1. Manually clean HAPI: `docker-compose -f docker-compose.test.yml down -v`
2. Restart fresh: `docker-compose -f docker-compose.test.yml up -d --force-recreate`

### Port Conflicts

**Symptom:** "Address already in use" error

**Solutions:**
1. Check ports 8081, 8001: `netstat -an | grep 8081`
2. Stop conflicting services
3. Change ports in `docker-compose.test.yml`

---

## Writing New Tests

### SDC Compliance Test Template

```python
import pytest

@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestNewSDCRequirement:
    """
    SDC Requirement: [Description]

    Reference: [SDC IG section]
    """

    async def test_requirement_name(self, api_client, load_test_fixtures):
        """
        Test: [What is being tested]

        Given: [Preconditions]
        When: [Action]
        Then: [Expected result]
        """
        # Arrange
        q_id = load_test_fixtures["phq2_questionnaire_id"]

        # Act
        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")

        # Assert
        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
class TestNewEndpoint:
    """Tests for [endpoint name]."""

    async def test_success_case(self, api_client, clean_questionnaire):
        """
        Test: [Description]
        """
        # Arrange
        q_id = await clean_questionnaire({...})

        # Act
        response = await api_client.get(f"/api/questionnaires/{q_id}")

        # Assert
        assert response.status_code == 200
```

---

## Best Practices

1. **Use descriptive test names** - `test_package_returns_collection_bundle` not `test_1`
2. **Follow Given-When-Then** - Clear test structure
3. **Reference SDC IG sections** - Link to specification
4. **Clean up resources** - Use `clean_*` fixtures
5. **Test failure scenarios** - Don't just test happy path
6. **Use markers** - Organize tests by category
7. **Keep tests independent** - No test should depend on another
8. **Mock sparingly** - Use real HAPI when possible
9. **Document expected behavior** - Docstrings for each test
10. **Run tests before commits** - Ensure nothing breaks

---

## Resources

- [SDC Implementation Guide](https://build.fhir.org/ig/HL7/sdc/)
- [SDC Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html)
- [FHIR R4 Specification](https://www.hl7.org/fhir/R4/)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

## Contact

For questions or issues with the test suite, please open an issue in the repository.
