# Testing Guide - Quick Start

## Overview

This project includes a comprehensive test suite that validates:
- ✅ **SDC Compliance** - Meets HL7 FHIR SDC Form Manager specification
- ✅ **Integration Testing** - Tests against real HAPI FHIR server
- ✅ **Failure Scenarios** - Error handling and edge cases

---

## Quick Start

### 1. Install Dependencies

```bash
cd api
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Start Test Environment

```bash
# From project root
docker-compose -f docker-compose.test.yml up -d
```

This starts:
- **HAPI FHIR Test Server** → `localhost:8081`
- **FastAPI Test Server** → `localhost:8001`

### 3. Run Tests

```bash
cd api

# Run all tests
pytest tests/ -v

# Run SDC compliance tests only
pytest tests/sdc_compliance/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### 4. View Results

```bash
# Open coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### 5. Cleanup

```bash
docker-compose -f docker-compose.test.yml down -v
```

---

## Test Categories

### SDC Compliance Tests 📋

Tests that validate SDC Form Manager specification compliance:

```bash
pytest tests/sdc_compliance/ -v
```

**What it tests:**
- $package operation returns correct Bundle structure
- All dependencies (ValueSets, CodeSystems, Libraries) included
- Missing dependencies generate OperationOutcome warnings
- Supports all three endpoint variants (instance, type-level, canonical URL)
- Bundle has correct SDC tags and metadata

**Reference:** [SDC IG Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html)

---

### Integration Tests 🔗

Tests FastAPI proxy to HAPI FHIR with real server:

```bash
pytest tests/integration/ -v
```

**What it tests:**
- Create, Read, Update, Delete (CRUD) operations
- Search functionality (by status, title, etc.)
- Error handling (404, 400, 500)
- Concurrent modifications
- Large payload handling

---

### Failure Scenario Tests ⚠️

Tests error handling and edge cases:

```bash
pytest -m failure_scenarios -v
```

**What it tests:**
- HAPI server unreachable
- Malformed JSON
- Invalid resource types
- Network timeouts
- Concurrent updates

---

## Common Commands

```bash
# Run specific test file
pytest tests/sdc_compliance/test_package_operation.py -v

# Run specific test
pytest tests/sdc_compliance/test_package_operation.py::TestSDCPackageOperationCompliance::test_package_returns_collection_bundle -v

# Run tests with specific marker
pytest -m sdc_compliance -v

# Run with detailed output
pytest tests/ -v --tb=short --capture=no

# Run fast tests only (skip slow ones)
pytest -m "not slow" -v

# Generate coverage report
pytest tests/ --cov=app --cov-report=html --cov-report=term
```

---

## Test Markers

| Marker | Description | Command |
|--------|-------------|---------|
| `sdc_compliance` | SDC specification tests | `pytest -m sdc_compliance` |
| `integration` | Tests with HAPI FHIR | `pytest -m integration` |
| `failure_scenarios` | Error handling tests | `pytest -m failure_scenarios` |
| `slow` | Slow-running tests | `pytest -m slow` |

---

## CI/CD

Tests run automatically on:
- Push to `master`, `main`, `develop` branches
- Pull requests

**GitHub Actions workflow:** `.github/workflows/test.yml`

**View results:** Check the "Actions" tab in GitHub

---

## Troubleshooting

### Problem: "HAPI FHIR not ready after 120 seconds"

**Solution:**
```bash
# Check Docker is running
docker ps

# View HAPI logs
docker logs hapi-fhir-test

# Restart containers
docker-compose -f docker-compose.test.yml restart
```

---

### Problem: Tests fail with port conflicts

**Solution:**
```bash
# Check what's using ports 8081, 8001
netstat -an | grep 8081
netstat -an | grep 8001

# Stop existing containers
docker-compose -f docker-compose.test.yml down

# Or change ports in docker-compose.test.yml
```

---

### Problem: Fixtures not cleaning up

**Solution:**
```bash
# Completely reset test environment
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d --force-recreate
```

---

### Problem: Tests hanging indefinitely

**Solution:**
```bash
# Check if services are responding
curl http://localhost:8001/health
curl http://localhost:8081/fhir/metadata

# View logs
docker-compose -f docker-compose.test.yml logs -f
```

---

## Test Data

Sample FHIR resources used in tests:

| Resource | Description | File |
|----------|-------------|------|
| PHQ-2 Questionnaire | Depression screening | `tests/fixtures/sample_resources.py` |
| PHQ-2 ValueSet | Frequency answers | `tests/fixtures/sample_resources.py` |
| Diabetes Questionnaire | Risk assessment | `tests/fixtures/sample_resources.py` |
| Simple Text Questionnaire | No dependencies | `tests/fixtures/sample_resources.py` |

---

## Writing New Tests

### Example SDC Compliance Test

```python
import pytest

@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestMyNewRequirement:
    """
    SDC Requirement: [Description]
    Reference: [SDC IG section]
    """

    async def test_my_requirement(self, api_client, load_test_fixtures):
        """
        Test: [What is being tested]

        Given: [Preconditions]
        When: [Action]
        Then: [Expected result]
        """
        # Test code here
        pass
```

---

## Resources

- **Full Test Documentation**: `api/tests/README.md`
- **SDC Implementation Guide**: https://build.fhir.org/ig/HL7/sdc/
- **pytest Documentation**: https://docs.pytest.org/
- **FHIR R4 Specification**: https://www.hl7.org/fhir/R4/

---

## Coverage Goals

| Component | Target | Status |
|-----------|--------|--------|
| Package Service | 90% | 🎯 |
| Dependency Resolver | 95% | 🎯 |
| API Endpoints | 80% | 🎯 |
| Overall | 85% | 🎯 |

---

## Summary

```bash
# Complete test workflow
cd api
pip install -r requirements.txt -r requirements-test.txt
cd ..
docker-compose -f docker-compose.test.yml up -d
cd api
pytest tests/ -v --cov=app --cov-report=html
docker-compose -f docker-compose.test.yml down -v
```

**Questions?** See `api/tests/README.md` for detailed documentation.
