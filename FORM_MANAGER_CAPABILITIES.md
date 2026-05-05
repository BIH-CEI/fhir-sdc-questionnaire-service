# Form Manager Capabilities & Workflow

## Current Capabilities

### ✅ Terminology Services

Your HAPI FHIR server has **robust terminology capabilities** despite not fetching the R5 terminology package:

#### Available Resources
- **840 ValueSets** - Pre-loaded from SDC and base FHIR specs
- **911 CodeSystems** - Including MII PROS and base FHIR terminologies
- **Active terminology operations**:
  - `ValueSet/$expand` - Expand value sets (tested & working)
  - `ValueSet/$validate-code` - Validate codes against value sets
  - `CodeSystem/$lookup` - Look up code details
  - `CodeSystem/$validate-code` - Validate codes

#### What You Have
- **Core FHIR R4 terminologies** - Built into the HAPI FHIR base
- **SDC-specific terminologies** - From hl7.fhir.uv.sdc#3.0.0
- **MII PROS terminologies** - From de.medizininformatikinitiative.kerndatensatz.pros#2026.2.0:
  - 5 CodeSystems (PRO-specific)
  - 9 ValueSets (PRO-specific)

#### What You're Missing
- **hl7.terminology.r4 package** - Contains extended terminology resources (would add ~1000+ more CodeSystems/ValueSets)
- **Impact**: Minimal for SDC form management - you have all the core terminologies needed for questionnaires

### ✅ Clinical Reasoning Module

Enabled via `hapi.fhir.cr.enabled: true`, providing SDC operations:

- `Questionnaire/$populate` - Pre-fill questionnaires with patient data using CQL
- `QuestionnaireResponse/$extract` - Extract structured FHIR resources from responses
- `Questionnaire/$package` - Bundle questionnaires with dependencies
- Additional CR operations for PlanDefinitions, Libraries, etc.

### ✅ Core FHIR Resources

Full CRUD support for:
- **Questionnaire** - Form definitions
- **QuestionnaireResponse** - Completed forms
- **ValueSet** - Value set definitions
- **CodeSystem** - Code system definitions
- **Library** - CQL libraries for advanced logic
- **StructureDefinition** - Profiles and extensions
- **ConceptMap** - Code mappings

### ✅ Validation

- **Profile validation** enabled (`validation.enabled: true`)
- **Request validation** enabled (`validation.requests_enabled: true`)
- Validates against SDC and MII PROS profiles

---

## Recommended Form Manager Workflow

### 1. **Form Design & Authoring Phase**

**Actors**: Clinical SMEs, Form Designers, Informaticians

#### 1.1 Define Terminologies
```bash
# Create custom CodeSystems for your domain
POST /fhir/CodeSystem
{
  "resourceType": "CodeSystem",
  "url": "http://example.org/CodeSystem/pain-scale",
  "status": "active",
  "content": "complete",
  "concept": [
    { "code": "0", "display": "No pain" },
    { "code": "10", "display": "Worst pain" }
  ]
}

# Create ValueSets referencing CodeSystems
POST /fhir/ValueSet
{
  "resourceType": "ValueSet",
  "url": "http://example.org/ValueSet/pain-assessment",
  "status": "active",
  "compose": {
    "include": [
      { "system": "http://example.org/CodeSystem/pain-scale" }
    ]
  }
}
```

#### 1.2 Create Questionnaires
```bash
# Create base questionnaire (draft status)
POST /fhir/Questionnaire
{
  "resourceType": "Questionnaire",
  "status": "draft",
  "title": "Pain Assessment Form",
  "item": [
    {
      "linkId": "1",
      "text": "Current pain level",
      "type": "choice",
      "answerValueSet": "http://example.org/ValueSet/pain-assessment"
    }
  ]
}
```

#### 1.3 Version Control
- Use `Questionnaire.version` for semantic versioning
- Use `Questionnaire.status`: `draft` → `active` → `retired`
- Consider using `Questionnaire.experimental: true` for testing

---

### 2. **Form Publishing Phase**

**Actors**: Form Managers, Governance Committees

#### 2.1 Validate Questionnaire
```bash
# Validate against SDC profiles
POST /fhir/Questionnaire/$validate
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "resource",
      "resource": { /* Questionnaire */ }
    },
    {
      "name": "profile",
      "valueUri": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire"
    }
  ]
}
```

#### 2.2 Expand Dependencies
```bash
# Ensure all ValueSets are expanded
GET /fhir/ValueSet/$expand?url=http://example.org/ValueSet/pain-assessment
```

#### 2.3 Activate Questionnaire
```bash
# Update status to active
PUT /fhir/Questionnaire/{id}
{
  "resourceType": "Questionnaire",
  "id": "{id}",
  "status": "active",  # Changed from draft
  "date": "2025-11-24",
  "effectivePeriod": {
    "start": "2025-12-01"
  }
  # ... rest of questionnaire
}
```

#### 2.4 Package for Distribution
```bash
# Create bundle with all dependencies
GET /fhir/Questionnaire/{id}/$package

# Returns Bundle containing:
# - Questionnaire
# - All referenced ValueSets
# - All referenced CodeSystems
# - All referenced Libraries (if CQL used)
```

---

### 3. **Form Filling Phase**

**Actors**: Clinicians, Patients, Data Entry Staff

#### 3.1 Retrieve Active Questionnaire
```bash
# Search for active questionnaires
GET /fhir/Questionnaire?status=active&_sort=-date

# Get specific questionnaire
GET /fhir/Questionnaire/{id}
```

#### 3.2 Pre-populate Form (Optional)
```bash
# Use $populate to pre-fill with patient data
POST /fhir/Questionnaire/{id}/$populate
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "subject",
      "valueReference": { "reference": "Patient/123" }
    },
    {
      "name": "local",
      "valueReference": { "reference": "Observation/456" }  # Context data
    }
  ]
}

# Returns: Pre-filled QuestionnaireResponse
```

#### 3.3 Render Form
- Use a form renderer (LHC Forms, SMART on FHIR apps, custom UI)
- Render based on `Questionnaire.item` structure
- Handle:
  - `enableWhen` conditions
  - `required` fields
  - `answerOption` or `answerValueSet` choices
  - `initial` values

#### 3.4 Complete & Submit Response
```bash
# Create QuestionnaireResponse
POST /fhir/QuestionnaireResponse
{
  "resourceType": "QuestionnaireResponse",
  "questionnaire": "Questionnaire/{id}",
  "status": "completed",
  "subject": { "reference": "Patient/123" },
  "authored": "2025-11-24T10:30:00Z",
  "author": { "reference": "Practitioner/789" },
  "item": [
    {
      "linkId": "1",
      "answer": [
        { "valueCoding": { "code": "5", "display": "Moderate pain" } }
      ]
    }
  ]
}
```

---

### 4. **Data Extraction Phase**

**Actors**: Backend Systems, ETL Processes, Analytics

#### 4.1 Extract Structured Data
```bash
# Use $extract to create FHIR resources from response
POST /fhir/QuestionnaireResponse/{id}/$extract

# If Questionnaire has SDC extraction extensions:
# - sdc-questionnaire-observationExtract
# - sdc-questionnaire-itemExtractionContext
# - targetStructureMap reference

# Returns: Transaction Bundle with extracted resources
# e.g., Observations, Conditions, Procedures
```

#### 4.2 Store Extracted Resources
```bash
# If $extract returns a transaction bundle
POST /fhir
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [
    {
      "request": { "method": "POST", "url": "Observation" },
      "resource": { /* Extracted Observation */ }
    }
  ]
}
```

---

### 5. **Analysis & Reporting Phase**

**Actors**: Researchers, Quality Improvement Teams, Administrators

#### 5.1 Search Responses
```bash
# Find all responses for a questionnaire
GET /fhir/QuestionnaireResponse?questionnaire=Questionnaire/{id}

# Filter by patient
GET /fhir/QuestionnaireResponse?subject=Patient/123

# Filter by date range
GET /fhir/QuestionnaireResponse?authored=ge2025-01-01&authored=lt2025-12-31

# Filter by status
GET /fhir/QuestionnaireResponse?status=completed
```

#### 5.2 Query Extracted Data
```bash
# Search extracted Observations
GET /fhir/Observation?based-on=QuestionnaireResponse/{id}

# Or by code
GET /fhir/Observation?code=http://example.org/CodeSystem/pain-scale|5
```

#### 5.3 Aggregate Data
```bash
# Use FHIR Bulk Data export
GET /fhir/$export?_type=QuestionnaireResponse,Observation

# Or implement custom analytics endpoints in FastAPI layer
```

---

### 6. **Form Lifecycle Management**

#### 6.1 Versioning Strategy
```
Example version progression:
- v1.0.0 (draft) → v1.0.0 (active)
- v1.1.0 (draft) → v1.1.0 (active)  # Minor update
- v2.0.0 (draft) → v2.0.0 (active)  # Breaking change

Previous versions:
- v1.0.0 (retired)
```

#### 6.2 Update Questionnaire
```bash
# Create new version
POST /fhir/Questionnaire
{
  "resourceType": "Questionnaire",
  "url": "http://example.org/Questionnaire/pain-assessment",  # Same canonical URL
  "version": "1.1.0",  # New version
  "status": "draft",
  "title": "Pain Assessment Form v1.1",
  # ... updates
}

# After testing, activate
PUT /fhir/Questionnaire/{new-id}
{ "status": "active" }

# Retire old version
PUT /fhir/Questionnaire/{old-id}
{ "status": "retired", "effectivePeriod": { "end": "2025-11-30" } }
```

#### 6.3 Deprecation Process
1. **Announce**: Set `Questionnaire.experimental: false` → `true`
2. **Parallel run**: Keep both versions active for transition period
3. **Retire old**: Update old version status to `retired`
4. **Archive**: Keep for historical reference (don't delete)

---

## Advanced Workflows

### Adaptive Forms (Conditional Logic)

Use `enableWhen` for dynamic questionnaires:

```json
{
  "linkId": "2",
  "text": "Please describe your pain",
  "type": "text",
  "enableWhen": [
    {
      "question": "1",
      "operator": ">=",
      "answerCoding": { "code": "5" }
    }
  ]
}
```

### Calculated Values

Use CQL libraries with `calculatedExpression` extension:

```json
{
  "linkId": "bmi",
  "text": "BMI (calculated)",
  "type": "decimal",
  "extension": [
    {
      "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
      "valueExpression": {
        "language": "text/cql",
        "expression": "%weight / (%height * %height)"
      }
    }
  ]
}
```

### Modular Questionnaires

Use `subQuestionnaire` extension for reusable components:

```json
{
  "linkId": "demographics",
  "text": "Patient Demographics",
  "type": "group",
  "extension": [
    {
      "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-subQuestionnaire",
      "valueCanonical": "http://example.org/Questionnaire/demographics-module"
    }
  ]
}
```

---

## Best Practices

### 1. Terminology Management
- ✅ **Pre-expand ValueSets** before deployment
- ✅ **Version your CodeSystems** using `CodeSystem.version`
- ✅ **Use canonical URLs** for all terminologies
- ⚠️ **Avoid inline codes** - always reference CodeSystems

### 2. Questionnaire Design
- ✅ **Use linkId** as stable identifiers (don't change across versions)
- ✅ **Leverage SDC profiles** (sdc-questionnaire, sdc-questionnaire-populate)
- ✅ **Add metadata**: publisher, contact, copyright, purpose
- ✅ **Test with real data** before activating

### 3. Data Extraction
- ✅ **Define extraction context** using SDC extensions
- ✅ **Use StructureMaps** for complex transformations
- ✅ **Validate extracted resources** before storage

### 4. Performance
- ✅ **Index frequently searched fields** (QuestionnaireResponse.authored, .subject)
- ✅ **Use _summary=count** for count queries
- ✅ **Implement pagination** for large result sets
- ✅ **Cache expanded ValueSets** in client applications

---

## Terminology Capabilities Summary

| Feature | Status | Notes |
|---------|--------|-------|
| ValueSet expansion | ✅ Working | 840 ValueSets available |
| CodeSystem lookup | ✅ Working | 911 CodeSystems available |
| Code validation | ✅ Working | Against loaded terminologies |
| External terminology | ❌ Not configured | Could add tx.fhir.org if needed |
| R4 base terminologies | ✅ Included | Part of FHIR R4 spec |
| SDC terminologies | ✅ Included | From SDC IG |
| MII PROS terminologies | ✅ Included | From MII PROS package |
| HL7 Terminology (extended) | ❌ Skipped | Would need R4-compatible version |

### Should You Add HL7 Terminology?

**Add if you need**:
- Extensive LOINC, SNOMED, ICD-10 codes
- HL7 v2/v3 code system mappings
- Country-specific code systems

**Skip if**:
- Working with custom/domain-specific terminologies
- Using external terminology service
- Performance/storage concerns

**How to add** (if needed):
```yaml
# In hapi-config/application.yaml
terminology:
  name: hl7.terminology.r4
  version: 5.5.0  # Last R4-compatible version
  installMode: STORE_ONLY
  fetchDependencies: false
```

---

## Next Steps

1. **Test the workflow** with a sample questionnaire
2. **Implement FastAPI endpoints** for common operations
3. **Build a form renderer** UI (React + LHC Forms)
4. **Set up analytics** dashboards for response data
5. **Configure backup strategy** for questionnaires and responses

## References

- [SDC Implementation Guide](https://build.fhir.org/ig/HL7/sdc/)
- [SDC Form Manager Capability Statement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html)
- [HAPI FHIR Clinical Reasoning](https://hapifhir.io/hapi-fhir/docs/clinical_reasoning/introduction.html)
