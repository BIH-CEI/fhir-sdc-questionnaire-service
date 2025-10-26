# FHIR Validator Integration

Complement your pytest suite with **official HL7 FHIR validation** for comprehensive testing.

## Why Use FHIR Validator?

Your pytest suite tests **behavior** and **SDC operations**.
FHIR Validator tests **structure** and **profile conformance**.

| Tool | Tests | Speed | Use Case |
|------|-------|-------|----------|
| **Pytest Suite** | Operations, workflows, multi-server | Fast | CI/CD, development |
| **FHIR Validator** | Structure, profiles, cardinality | Medium | Release validation |
| **Touchstone** | Full SDC certification | Slow | Official certification |

**Best Practice**: Use all three! ✅

## Quick Start (5 minutes)

### 1. Download FHIR Validator
```bash
cd tools
wget https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar
# Or manually download from: https://github.com/hapifhir/org.hl7.fhir.core/releases
```

### 2. Validate a Questionnaire
```bash
java -jar tools/validator_cli.jar \
  api/tests/fixtures/sample_resources.py \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc
```

### 3. Integrate with Tests
```bash
# Validate before running tests
./validate-resources.sh && pytest tests/ -v
```

## Integration Options

### Option 1: Pre-commit Hook (Recommended)
```bash
# .git/hooks/pre-commit
#!/bin/bash
echo "Validating FHIR resources..."

java -jar tools/validator_cli.jar \
  api/tests/fixtures/sample_resources.py \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -quiet

if [ $? -ne 0 ]; then
    echo "❌ FHIR validation failed!"
    exit 1
fi

echo "✅ FHIR validation passed!"
```

### Option 2: Pytest Plugin
```python
# api/tests/test_fhir_validation.py
import pytest
import subprocess
import json

@pytest.mark.validation
class TestFHIRValidation:
    """Validate resources using official FHIR Validator."""

    def test_questionnaire_profiles(self):
        """Validate all Questionnaires against SDC profiles."""
        result = subprocess.run([
            "java", "-jar", "tools/validator_cli.jar",
            "api/tests/fixtures/sample_resources.py",
            "-version", "4.0",
            "-ig", "hl7.fhir.uv.sdc",
            "-output-style", "json"
        ], capture_output=True, text=True)

        if result.returncode != 0:
            validation_results = json.loads(result.stdout)
            # Parse and assert on specific errors
            errors = [issue for issue in validation_results["issues"]
                     if issue["severity"] == "error"]
            assert len(errors) == 0, f"Validation errors: {errors}"
```

### Option 3: CI/CD Pipeline
```yaml
# .github/workflows/validate.yml
name: FHIR Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          java-version: '17'

      - name: Download FHIR Validator
        run: |
          mkdir -p tools
          wget -O tools/validator_cli.jar \
            https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar

      - name: Validate Resources
        run: |
          java -jar tools/validator_cli.jar \
            api/tests/fixtures/ \
            -version 4.0 \
            -ig hl7.fhir.uv.sdc \
            -recursive

      - name: Run Pytest Suite
        run: |
          cd api
          pip install -r requirements.txt -r requirements-test.txt
          pytest tests/ -v
```

## Validation Scenarios

### Validate SDC Profiles
```bash
# Validate against SDC Questionnaire profile
java -jar tools/validator_cli.jar \
  questionnaire.json \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -profile http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire
```

### Validate All Test Fixtures
```bash
# Recursive validation
java -jar tools/validator_cli.jar \
  api/tests/fixtures/ \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -recursive \
  -output-style compact
```

### Validate Against Multiple Profiles
```bash
# Advanced Rendering + Adaptive profiles
java -jar tools/validator_cli.jar \
  questionnaire.json \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -profile http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-render \
  -profile http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-adapt
```

## Validation Script

Create `validate-resources.sh`:

```bash
#!/bin/bash

# FHIR Resource Validation Script

VALIDATOR="tools/validator_cli.jar"
FIXTURES_DIR="api/tests/fixtures"
FHIR_VERSION="4.0"
IG="hl7.fhir.uv.sdc"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔍 FHIR Validation Starting..."

# Check if validator exists
if [ ! -f "$VALIDATOR" ]; then
    echo "❌ Validator not found. Downloading..."
    mkdir -p tools
    wget -O "$VALIDATOR" \
        https://github.com/hapifhir/org.hl7.fhir.core/releases/latest/download/validator_cli.jar
fi

# Run validation
java -jar "$VALIDATOR" \
    "$FIXTURES_DIR" \
    -version "$FHIR_VERSION" \
    -ig "$IG" \
    -recursive \
    -output-style compact

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All resources valid!${NC}"
    exit 0
else
    echo -e "${RED}❌ Validation failed!${NC}"
    exit 1
fi
```

Make it executable:
```bash
chmod +x validate-resources.sh
./validate-resources.sh
```

## Common Validation Issues

### Issue: Missing Profiles
```
Error: Unknown profile http://hl7.org/fhir/uv/sdc/...
```

**Solution**: Load SDC IG
```bash
java -jar validator_cli.jar questionnaire.json \
  -ig hl7.fhir.uv.sdc  # ← Add this
```

### Issue: Cardinality Violations
```
Error: Element 'status' is required (min=1)
```

**Solution**: Fix resource structure
```json
{
  "resourceType": "Questionnaire",
  "status": "active",  // ← Add required fields
  "item": []
}
```

### Issue: Invalid Code
```
Error: Code 'invalid' not in ValueSet
```

**Solution**: Use valid codes from ValueSet
```json
{
  "status": "active"  // ← Use: draft, active, retired
}
```

## Advanced Usage

### Custom Validation Rules
```bash
# Validate with custom StructureDefinition
java -jar validator_cli.jar \
  questionnaire.json \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -ig custom-profiles/ \
  -profile http://myorg.com/StructureDefinition/custom-questionnaire
```

### Snapshot Generation
```bash
# Generate snapshots for profiles
java -jar validator_cli.jar \
  -convert \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -source profile.json \
  -output profile-snapshot.json
```

### Batch Validation Report
```bash
# Generate HTML report
java -jar validator_cli.jar \
  api/tests/fixtures/ \
  -version 4.0 \
  -ig hl7.fhir.uv.sdc \
  -recursive \
  -html-output validation-report.html

# View report
open validation-report.html  # macOS
start validation-report.html  # Windows
```

## Touchstone Integration (Official Certification)

For official SDC certification, use Touchstone:

### 1. Sign up at [touchstone.aegis.net](https://touchstone.aegis.net)

### 2. Upload your server details
- FHIR endpoint: `http://your-server:8080/fhir`
- Conformance statement: `http://your-server:8080/fhir/metadata`

### 3. Run SDC Test Suite
- Select: **SDC Form Manager** test suite
- Execute all tests
- Download certification report

### 4. Address failures
- Review failed tests
- Update implementation
- Re-run tests

## Recommended Testing Flow

```
┌─────────────────────────────────────────────────┐
│  1. Local Development                           │
│     ├─ pytest tests/ -v                         │
│     └─ ./validate-resources.sh                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  2. Pre-Commit Hook                             │
│     ├─ FHIR Validator (structure)               │
│     └─ pytest tests/sdc_compliance/ (behavior)  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  3. CI/CD Pipeline                              │
│     ├─ Multi-server pytest                      │
│     ├─ FHIR Validator                           │
│     └─ Code coverage                            │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  4. Release Validation                          │
│     ├─ Full pytest suite                        │
│     ├─ FHIR Validator report                    │
│     └─ Touchstone certification (optional)      │
└─────────────────────────────────────────────────┘
```

## Resources

- **FHIR Validator**: https://confluence.hl7.org/display/FHIR/Using+the+FHIR+Validator
- **Touchstone**: https://touchstone.aegis.net
- **SDC IG**: https://build.fhir.org/ig/HL7/sdc/
- **Inferno**: https://inferno.healthit.gov/
