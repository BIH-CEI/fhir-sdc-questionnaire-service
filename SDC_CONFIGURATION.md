# SDC Form Manager Configuration

This document describes the configuration changes made to enable SDC (Structured Data Capture) compliance for the HAPI FHIR server.

## Changes Made

### 1. Added SDC Implementation Guide (`hapi-config/application.yaml`)

```yaml
sdc:
  name: hl7.fhir.uv.sdc
  version: 3.0.0
  installMode: STORE_AND_INSTALL
  reloadExisting: false
  fetchDependencies: true
```

**What this does:**
- Downloads and installs the HL7 FHIR SDC Implementation Guide v3.0.0
- Imports SDC-specific Questionnaire profiles and resources into the database
- Makes them searchable and available for validation
- Automatically fetches required dependencies

### 2. Enabled Clinical Reasoning/CQL (`docker-compose.yml`)

```yaml
hapi.fhir.cql_enabled: true
```

**What this does:**
- Enables the Clinical Query Language (CQL) engine
- Required for advanced Questionnaire operations:
  - `$populate` - Pre-fill questionnaires with patient data
  - `$extract` - Extract structured resources from QuestionnaireResponses
  - `$questionnaire` - Generate questionnaires from StructureDefinitions
  - `$package` - Bundle questionnaires with dependencies

## Verifying the Configuration

When you start the server on another computer, you can verify SDC support is enabled:

### 1. Check the Capability Statement

```bash
curl http://localhost:8080/fhir/metadata?_format=json | jq '.rest[0].resource[] | select(.type=="Questionnaire")'
```

Look for:
- `Questionnaire` resource with CRUD operations
- Operations listed in the `operation` array

### 2. Check for SDC Operations

```bash
curl http://localhost:8080/fhir/metadata?_format=json | jq '.rest[0].resource[] | select(.type=="Questionnaire") | .operation'
```

You should see operations like:
- `$populate`
- `$extract`
- `$questionnaire`
- `$package`

### 3. Check Installed Implementation Guides

You can query the server logs during startup to see:
```
Installing implementation guide: hl7.fhir.uv.sdc#3.0.0
```

Or check via the Package endpoint (if available):
```bash
curl http://localhost:8080/fhir/ImplementationGuide?url=http://hl7.org/fhir/uv/sdc/ImplementationGuide/hl7.fhir.uv.sdc
```

### 4. Test Basic Questionnaire Operations

Create a simple questionnaire:
```bash
curl -X POST http://localhost:8080/fhir/Questionnaire \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "Questionnaire",
    "status": "draft",
    "item": [{
      "linkId": "1",
      "text": "What is your name?",
      "type": "string"
    }]
  }'
```

Then try to populate it:
```bash
curl -X POST "http://localhost:8080/fhir/Questionnaire/[ID]/$populate?subject=Patient/example"
```

## SDC Form Manager Compliance

With these changes, your HAPI FHIR server should now support the core requirements of the [SDC Form Manager capability statement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html):

### Supported Resources (SHALL)
- ✅ Questionnaire (Read, Create, Update, Delete)
- ✅ ValueSet (Read, Create, Update, Delete)
- ✅ CodeSystem (Read, Create, Update, Delete)
- ✅ Library (Read, Create, Update, Delete)

### Supported Operations
- ✅ `$populate` - Pre-fill questionnaires
- ✅ `$extract` - Extract data from responses
- ✅ `$questionnaire` - Generate questionnaires
- ✅ `$package` - Bundle with dependencies
- ⚠️ `$assemble` - May not be supported out-of-box in HAPI (needs verification)

### Search Parameters
HAPI FHIR supports all standard FHIR search parameters for these resources by default.

## Next Steps

1. **Start the server** on a computer with Docker
2. **Verify the configuration** using the commands above
3. **Test SDC operations** with sample questionnaires
4. **Check if `$assemble` is available** (may require additional configuration or custom implementation)
5. **Review server logs** for any errors during IG installation

## Troubleshooting

### IG Installation Fails
- Check internet connectivity (needs to download from packages.fhir.org)
- Verify the version number is correct
- Check server logs for detailed error messages

### CQL Operations Not Available
- Ensure `hapi.fhir.cql_enabled: true` is set
- Check if the HAPI FHIR version supports CQL (should be 5.4.0+)
- Review server startup logs for CQL initialization messages

### Performance Issues
- First startup will be slow (downloading and installing IGs)
- Set `reloadExisting: false` to avoid reinstalling on every restart
- Consider using `installMode: STORE_ONLY` if you only need validation

## References

- [SDC Implementation Guide](https://build.fhir.org/ig/HL7/sdc/)
- [SDC Form Manager Capability Statement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html)
- [HAPI FHIR Clinical Reasoning Documentation](https://hapifhir.io/hapi-fhir/docs/clinical_reasoning/questionnaires.html)
- [HAPI FHIR Implementation Guides](https://hapifhir.io/hapi-fhir/docs/server_jpa/configuration.html#implementation-guides)
