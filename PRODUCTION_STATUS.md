# Production HAPI FHIR Server Status

**Last Updated**: 2025-11-12
**Server URL**: http://localhost:8080/fhir

---

## Current Configuration Summary

### ✅ Enabled Features

1. **Clinical Reasoning Module** - Fully operational
   - `$populate` operation available
   - `$package` operation available
   - `$extract` operation (CR module)
   - `$data-requirements` operation

2. **SDC Implementation Guide 3.0.0** - Fully loaded
   - Installation mode: STORE_AND_INSTALL
   - Dependencies fetched: Yes
   - Status: ✅ Searchable and functional

3. **ISiK 5.1.0 (German Interoperability Standard)** - Loaded with limitations
   - Installation mode: STORE_ONLY (workaround)
   - Dependencies fetched: No
   - Status: ⚠️ Resources indexed but NOT searchable via FHIR API
   - Includes: Formulare module for Questionnaires

### ❌ Disabled Features

1. **FHIR Validation** - Completely disabled
   - Reason: ISiK snapshot generation causes Hibernate Search initialization error
   - Trade-off: Resources won't be validated against profiles during storage
   - Configuration: `validation.enabled: false` and `validation.requests_enabled: false`

2. **MII PRO IG** - Commented out
   - Reason: Package requires Simplifier authentication (pre-release ballot)
   - Package URL: https://packages.simplifier.net/de.medizininformatikinitiative.kerndatensatz.pro/2026.0.0-ballot
   - Status: Can be re-enabled once authentication is configured

---

## Configuration Files

### 1. application.yaml
Location: `hapi-config/application.yaml`

Key settings:
```yaml
hapi:
  fhir:
    fhir_version: R4

    cr:
      enabled: true  # Clinical Reasoning Module

    implementationguides:
      sdc:
        name: hl7.fhir.uv.sdc
        version: 3.0.0
        installMode: STORE_AND_INSTALL
        reloadExisting: false
        fetchDependencies: true

      isik:
        name: de.gematik.isik
        version: 5.1.0
        installMode: STORE_ONLY  # Workaround for snapshot error
        reloadExisting: false
        fetchDependencies: false

    validation:
      enabled: false  # Disabled to bypass ISiK snapshot generation
      requests_enabled: false
```

### 2. docker-compose.yml
Key environment variables:
```yaml
environment:
  SPRING_CONFIG_ADDITIONAL_LOCATION: file:/data/hapi/
  hapi.fhir.cr.enabled: true
  spring.datasource.url: jdbc:postgresql://db:5432/${POSTGRES_DB}
```

---

## Known Issues and Limitations

### 1. ISiK Profiles Not Searchable

**Issue**: ISiK 5.1.0 StructureDefinitions are loaded but cannot be searched via FHIR API

**Example**:
```bash
curl "http://localhost:8080/fhir/StructureDefinition?url=https://gematik.de/fhir/isik/StructureDefinition/ISiKFormularDefinition"
# Returns: "total": 0
```

**Reason**: Using `STORE_ONLY` installation mode to bypass snapshot generation error

**Impact**:
- ISiK profiles available for internal validation reference
- Not usable for creating conformant ISiK resources via API
- Cannot query ISiK-specific StructureDefinitions

**Workaround Options**:
1. Accept limitation (profiles for reference only)
2. Manually upload specific ISiK profiles needed
3. Wait for HAPI/ISiK compatibility fix in future versions

### 2. Snapshot Generation Error (Documented)

**Error Message**:
```
HAPI-1290: Failure when generating snapshot of StructureDefinition: StructureDefinition/ISiKKoerperkerntemperatur
Caused by: HSEARCH800001: Hibernate Search was not initialized.
```

**Affected Profiles**:
- ISiKKoerperkerntemperatur (body core temperature)
- Potentially other ISiK profiles

**Reason**: ISiK 5.1.0 StructureDefinition snapshot generation triggers Hibernate Search initialization before it's ready

**Current Solution**: Disabled validation entirely and use STORE_ONLY mode

### 3. Validation Disabled Globally

**Impact**:
- All resources (not just ISiK) stored without profile validation
- May allow non-conformant resources to be stored
- Testing and production should validate resources client-side

**Recommendation**: Re-enable validation once ISiK compatibility is resolved

---

## SDC Operations Available

Verified operational at http://localhost:8080/fhir:

| Operation | Resource | Endpoint Example |
|-----------|----------|------------------|
| $populate | Questionnaire | `GET /Questionnaire/{id}/$populate` |
| $package | Global/Questionnaire | `GET /Questionnaire/{id}/$package` |
| $extract | QuestionnaireResponse | `POST /QuestionnaireResponse/$extract` |
| $data-requirements | Library | `GET /Library/{id}/$data-requirements` |

**OperationDefinitions**:
- `populate`: http://localhost:8080/fhir/OperationDefinition/Questionnaire-it-populate
- `package`: http://localhost:8080/fhir/OperationDefinition/Global-it-package

---

## Implementation Guides Status

| IG | Version | Mode | Searchable | Dependencies | Status |
|----|---------|------|------------|--------------|--------|
| SDC | 3.0.0 | STORE_AND_INSTALL | ✅ Yes | ✅ Fetched | ✅ Fully functional |
| ISiK | 5.1.0 | STORE_ONLY | ❌ No | ❌ Disabled | ⚠️ Indexed, not searchable |
| MII PRO | 2026.0.0-ballot | N/A | N/A | N/A | ❌ Commented out (auth required) |

---

## Testing HAPI's Built-in $package Operation

Since HAPI now has Clinical Reasoning enabled with the $package operation, you can test it directly:

### Create a test Questionnaire:
```bash
curl -X POST http://localhost:8080/fhir/Questionnaire \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Questionnaire",
    "status": "active",
    "item": [
      {
        "linkId": "1",
        "text": "What is your name?",
        "type": "string"
      }
    ]
  }'
```

### Test $package operation:
```bash
# By instance ID
curl "http://localhost:8080/fhir/Questionnaire/{id}/$package"

# By canonical URL (if Questionnaire has a URL)
curl "http://localhost:8080/fhir/Questionnaire/$package?url=http://example.org/Questionnaire/test"
```

This can help determine if the FastAPI wrapper layer is still needed, or if HAPI's native implementation is sufficient.

---

## Architecture Implications

### Question: Is FastAPI Layer Still Needed?

**HAPI Now Provides**:
- ✅ $package operation
- ✅ $populate operation
- ✅ $extract operation
- ✅ SDC IG support

**FastAPI Custom Implementation Provides**:
- Custom business logic for dependency resolution
- Circular reference handling
- Custom error handling and validation
- Server-agnostic abstraction layer

**Recommendation**:
1. Test HAPI's native $package operation with real Questionnaires
2. Compare output Bundle structure with SDC requirements
3. Evaluate if HAPI's implementation meets all use cases
4. Decision: Keep FastAPI if custom logic needed, otherwise simplify architecture

---

## Startup Time

Current startup time: ~49 seconds

**Breakdown**:
- PostgreSQL initialization: ~5 seconds
- HAPI FHIR startup: ~40 seconds
- IG loading (SDC + ISiK): ~4 seconds

---

## Database

**Type**: PostgreSQL 15
**Container**: fhir-postgres
**Volumes**:
- postgres_data (persistent)
- hapi_data (HAPI work files)

**Clean Restart** (destroys data):
```bash
docker-compose down -v && docker-compose up -d
```

---

## Maintenance Notes

### Updating ISiK Version
1. Edit `hapi-config/application.yaml`
2. Change `isik.version` to desired version
3. Run `docker-compose down -v` to clear cached data
4. Run `docker-compose up -d`
5. Monitor logs for snapshot generation errors

### Re-enabling Validation
1. Edit `hapi-config/application.yaml`:
   ```yaml
   validation:
     enabled: true
     requests_enabled: true
   ```
2. Change ISiK to `installMode: STORE_AND_INSTALL`
3. Restart: `docker-compose restart hapi-fhir`
4. Check logs for snapshot generation errors

### Enabling MII PRO IG
1. Configure Simplifier authentication
2. Uncomment mii_pro section in `application.yaml`
3. Restart HAPI

---

## Next Steps

1. **Test HAPI's $package operation** with sample Questionnaires containing dependencies
2. **Compare with FastAPI implementation** to evaluate if custom layer is still needed
3. **Create example data** to test SDC workflows ($populate, $extract)
4. **Monitor for HAPI updates** that fix ISiK snapshot generation issues
5. **Consider re-enabling validation** once ISiK compatibility is confirmed

---

## Support Resources

- HAPI FHIR Documentation: https://hapifhir.io/
- SDC Implementation Guide: https://build.fhir.org/ig/HL7/sdc/
- ISiK Documentation: https://simplifier.net/isik
- Clinical Reasoning Module: https://hapifhir.io/hapi-fhir/docs/clinical_reasoning/overview.html
