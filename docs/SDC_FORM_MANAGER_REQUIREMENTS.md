# SDC Form Manager Requirements

**Reference:** [SDC Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html)

**FHIR Version:** R4 (4.0.1)

**Last Updated:** 2025-10-23

---

## Document Purpose

This document maps ALL requirements from the HL7 FHIR SDC Form Manager CapabilityStatement to unique requirement IDs for traceability to tests and implementation.

---

## Requirement ID Format

**Format:** `SDC-FM-[CATEGORY]-[NUMBER]-[LEVEL]`

- **CATEGORY:** Resource type or functional area (Q=Questionnaire, VS=ValueSet, OP=Operation, etc.)
- **NUMBER:** Sequential number within category
- **LEVEL:** Conformance level
  - `SHALL` = Mandatory (MUST implement)
  - `SHOULD` = Recommended (implement if possible)
  - `MAY` = Optional (nice to have)

**Example:** `SDC-FM-Q-001-SHALL` = Questionnaire requirement #1, mandatory

---

## Table of Contents

1. [Resource Support Requirements](#resource-support-requirements)
2. [Questionnaire Requirements](#questionnaire-requirements)
3. [ValueSet Requirements](#valueset-requirements)
4. [CodeSystem Requirements](#codesystem-requirements)
5. [Library Requirements](#library-requirements)
6. [Operation Requirements](#operation-requirements)
7. [Search Parameter Requirements](#search-parameter-requirements)
8. [Interaction Requirements](#interaction-requirements)

---

## Resource Support Requirements

### RES-001: Supported Resource Types

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-RES-001-SHALL | SHALL | Support Questionnaire resource type | CapabilityStatement.rest.resource |
| SDC-FM-RES-002-SHOULD | SHOULD | Support ValueSet resource type | CapabilityStatement.rest.resource |
| SDC-FM-RES-003-SHOULD | SHOULD | Support CodeSystem resource type | CapabilityStatement.rest.resource |
| SDC-FM-RES-004-MAY | MAY | Support Library resource type | CapabilityStatement.rest.resource |
| SDC-FM-RES-005-MAY | MAY | Support StructureMap resource type | CapabilityStatement.rest.resource |
| SDC-FM-RES-006-MAY | MAY | Support QuestionnaireResponse resource type | CapabilityStatement.rest.resource |

---

## Questionnaire Requirements

### Questionnaire Profile Support

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-Q-001-SHALL | SHALL | Support SDC Questionnaire profile | StructureDefinition/sdc-questionnaire |
| SDC-FM-Q-002-SHOULD | SHOULD | Support SDC Advanced Rendering Questionnaire profile | StructureDefinition/sdc-questionnaire-render |
| SDC-FM-Q-003-SHOULD | SHOULD | Support SDC Adaptive Questionnaire profile | StructureDefinition/sdc-questionnaire-adapt |

### Questionnaire Interactions

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-Q-010-SHALL | SHALL | Support read interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-011-SHALL | SHALL | Support search-type interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-012-SHOULD | SHOULD | Support create interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-013-SHOULD | SHOULD | Support update interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-014-MAY | MAY | Support delete interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-015-MAY | MAY | Support vread (version read) interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |
| SDC-FM-Q-016-MAY | MAY | Support history-instance interaction on Questionnaire | CapabilityStatement.rest.resource[Questionnaire].interaction |

### Questionnaire Search Parameters

| Req ID | Level | Description | Search Parameter |
|--------|-------|-------------|------------------|
| SDC-FM-Q-020-SHALL | SHALL | Support search by _id | _id |
| SDC-FM-Q-021-SHALL | SHALL | Support search by url | url |
| SDC-FM-Q-022-SHALL | SHALL | Support search by version | version |
| SDC-FM-Q-023-SHALL | SHALL | Support search by status | status |
| SDC-FM-Q-024-SHOULD | SHOULD | Support search by title | title |
| SDC-FM-Q-025-SHOULD | SHOULD | Support search by name | name |
| SDC-FM-Q-026-SHOULD | SHOULD | Support search by publisher | publisher |
| SDC-FM-Q-027-SHOULD | SHOULD | Support search by date | date |
| SDC-FM-Q-028-SHOULD | SHOULD | Support search by _lastUpdated | _lastUpdated |
| SDC-FM-Q-029-MAY | MAY | Support search by identifier | identifier |
| SDC-FM-Q-030-MAY | MAY | Support search by subject-type | subject-type |
| SDC-FM-Q-031-MAY | MAY | Support search by context | context |
| SDC-FM-Q-032-MAY | MAY | Support search by definition | definition |

### Questionnaire Search Modifiers

| Req ID | Level | Description | Modifier |
|--------|-------|-------------|----------|
| SDC-FM-Q-040-SHOULD | SHOULD | Support :contains modifier on title search | title:contains |
| SDC-FM-Q-041-SHOULD | SHOULD | Support :contains modifier on name search | name:contains |
| SDC-FM-Q-042-MAY | MAY | Support :exact modifier on string searches | :exact |

### Questionnaire Search Combinations

| Req ID | Level | Description | Example |
|--------|-------|-------------|---------|
| SDC-FM-Q-050-SHALL | SHALL | Support search by url + version | url={canonical}&version={version} |
| SDC-FM-Q-051-SHOULD | SHOULD | Support search by status + _sort | status=active&_sort=-_lastUpdated |
| SDC-FM-Q-052-MAY | MAY | Support _revinclude for QuestionnaireResponse | _revinclude=QuestionnaireResponse:questionnaire |

---

## ValueSet Requirements

### ValueSet Interactions

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-VS-010-SHOULD | SHOULD | Support read interaction on ValueSet | CapabilityStatement.rest.resource[ValueSet].interaction |
| SDC-FM-VS-011-SHOULD | SHOULD | Support search-type interaction on ValueSet | CapabilityStatement.rest.resource[ValueSet].interaction |
| SDC-FM-VS-012-MAY | MAY | Support create interaction on ValueSet | CapabilityStatement.rest.resource[ValueSet].interaction |
| SDC-FM-VS-013-MAY | MAY | Support update interaction on ValueSet | CapabilityStatement.rest.resource[ValueSet].interaction |

### ValueSet Search Parameters

| Req ID | Level | Description | Search Parameter |
|--------|-------|-------------|------------------|
| SDC-FM-VS-020-SHOULD | SHOULD | Support search by _id | _id |
| SDC-FM-VS-021-SHOULD | SHOULD | Support search by url | url |
| SDC-FM-VS-022-SHOULD | SHOULD | Support search by version | version |
| SDC-FM-VS-023-SHOULD | SHOULD | Support search by status | status |
| SDC-FM-VS-024-MAY | MAY | Support search by title | title |

### ValueSet Operations

| Req ID | Level | Description | Operation |
|--------|-------|-------------|-----------|
| SDC-FM-VS-030-SHOULD | SHOULD | Support $expand operation on ValueSet | $expand |
| SDC-FM-VS-031-MAY | MAY | Support $validate-code operation on ValueSet | $validate-code |

---

## CodeSystem Requirements

### CodeSystem Interactions

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-CS-010-SHOULD | SHOULD | Support read interaction on CodeSystem | CapabilityStatement.rest.resource[CodeSystem].interaction |
| SDC-FM-CS-011-MAY | MAY | Support search-type interaction on CodeSystem | CapabilityStatement.rest.resource[CodeSystem].interaction |

### CodeSystem Search Parameters

| Req ID | Level | Description | Search Parameter |
|--------|-------|-------------|------------------|
| SDC-FM-CS-020-SHOULD | SHOULD | Support search by url | url |
| SDC-FM-CS-021-MAY | MAY | Support search by version | version |

### CodeSystem Operations

| Req ID | Level | Description | Operation |
|--------|-------|-------------|-----------|
| SDC-FM-CS-030-MAY | MAY | Support $lookup operation on CodeSystem | $lookup |

---

## Library Requirements

### Library Interactions

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-LIB-010-MAY | MAY | Support read interaction on Library | CapabilityStatement.rest.resource[Library].interaction |
| SDC-FM-LIB-011-MAY | MAY | Support search-type interaction on Library | CapabilityStatement.rest.resource[Library].interaction |

### Library Search Parameters

| Req ID | Level | Description | Search Parameter |
|--------|-------|-------------|------------------|
| SDC-FM-LIB-020-MAY | MAY | Support search by url | url |
| SDC-FM-LIB-021-MAY | MAY | Support search by version | version |

---

## Operation Requirements

### $package Operation (Questionnaire)

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-OP-PKG-001-SHALL | SHALL | Support $package operation on Questionnaire (instance level) | OperationDefinition/Questionnaire-package |
| SDC-FM-OP-PKG-002-SHALL | SHALL | Support $package operation on Questionnaire (type level) | OperationDefinition/Questionnaire-package |
| SDC-FM-OP-PKG-003-SHALL | SHALL | Include Questionnaire in package Bundle | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-004-SHALL | SHALL | Include all referenced ValueSets in package Bundle | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-005-SHALL | SHALL | Include all referenced CodeSystems in package Bundle (transitive) | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-006-SHOULD | SHOULD | Include all referenced Libraries in package Bundle | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-007-SHOULD | SHOULD | Include all referenced StructureMaps in package Bundle | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-008-SHALL | SHALL | Return Bundle with type='collection' | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-009-SHOULD | SHOULD | Place Questionnaire as first entry in Bundle | SDC IG Best Practice |
| SDC-FM-OP-PKG-010-SHALL | SHALL | Support include-dependencies parameter (boolean, default=true) | OperationDefinition |
| SDC-FM-OP-PKG-011-SHALL | SHALL | Resolve dependencies by canonical URL | FHIR R4 Canonical |
| SDC-FM-OP-PKG-012-SHALL | SHALL | Support version-specific canonical URLs (url\|version) | FHIR R4 Canonical |
| SDC-FM-OP-PKG-013-SHOULD | SHOULD | Return OperationOutcome for missing dependencies (severity=warning) | SDC IG 3.2.1 |
| SDC-FM-OP-PKG-014-SHOULD | SHOULD | Handle circular dependencies without error | Implementation Best Practice |
| SDC-FM-OP-PKG-015-SHALL | SHALL | Return 404 if Questionnaire not found | HTTP Status Codes |
| SDC-FM-OP-PKG-016-MAY | MAY | Support url parameter for canonical URL resolution | OperationDefinition |
| SDC-FM-OP-PKG-017-MAY | MAY | Support version parameter when using url parameter | OperationDefinition |
| SDC-FM-OP-PKG-018-SHOULD | SHOULD | Add Bundle.meta.tag to indicate package type | Best Practice |
| SDC-FM-OP-PKG-019-MAY | MAY | Subset large CodeSystems to only referenced concepts | Performance Optimization |
| SDC-FM-OP-PKG-020-MAY | MAY | Cache package Bundles for performance | Performance Optimization |

### $populate Operation (Optional)

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-OP-POP-001-MAY | MAY | Support $populate operation on Questionnaire | OperationDefinition/Questionnaire-populate |
| SDC-FM-OP-POP-002-MAY | MAY | Accept subject parameter (Patient reference) | OperationDefinition |
| SDC-FM-OP-POP-003-MAY | MAY | Pre-populate QuestionnaireResponse with patient data | SDC IG 3.3 |
| SDC-FM-OP-POP-004-MAY | MAY | Execute CQL logic for calculated values | CQL Integration |

### $extract Operation (Optional)

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-OP-EXT-001-MAY | MAY | Support $extract operation on QuestionnaireResponse | OperationDefinition/QuestionnaireResponse-extract |
| SDC-FM-OP-EXT-002-MAY | MAY | Extract FHIR resources from QuestionnaireResponse | SDC IG 3.4 |
| SDC-FM-OP-EXT-003-MAY | MAY | Use StructureMap for extraction mapping | StructureMap Integration |

### $assemble Operation (Optional)

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-OP-ASM-001-MAY | MAY | Support $assemble operation on Questionnaire | OperationDefinition/Questionnaire-assemble |
| SDC-FM-OP-ASM-002-MAY | MAY | Compose modular Questionnaire from sub-Questionnaires | SDC IG Modular Forms |

---

## Search Parameter Requirements

### Common Search Parameters

| Req ID | Level | Description | Parameter |
|--------|-------|-------------|-----------|
| SDC-FM-SP-001-SHALL | SHALL | Support _id search parameter | _id |
| SDC-FM-SP-002-SHALL | SHALL | Support _lastUpdated search parameter | _lastUpdated |
| SDC-FM-SP-003-SHOULD | SHOULD | Support _sort search parameter | _sort |
| SDC-FM-SP-004-SHOULD | SHOULD | Support _count search parameter (pagination) | _count |
| SDC-FM-SP-005-MAY | MAY | Support _summary search parameter | _summary |
| SDC-FM-SP-006-MAY | MAY | Support _elements search parameter | _elements |
| SDC-FM-SP-007-MAY | MAY | Support _include search parameter | _include |
| SDC-FM-SP-008-MAY | MAY | Support _revinclude search parameter | _revinclude |

### Search Comparators

| Req ID | Level | Description | Comparator |
|--------|-------|-------------|------------|
| SDC-FM-SP-010-SHOULD | SHOULD | Support date comparators (eq, ne, gt, lt, ge, le) | date=[prefix][value] |
| SDC-FM-SP-011-MAY | MAY | Support string modifiers (:exact, :contains) | string:modifier |

---

## Interaction Requirements

### RESTful Interactions

| Req ID | Level | Description | HTTP Method |
|--------|-------|-------------|-------------|
| SDC-FM-INT-001-SHALL | SHALL | Support read interaction (GET {resourceType}/{id}) | GET |
| SDC-FM-INT-002-SHALL | SHALL | Support search interaction (GET {resourceType}?params) | GET |
| SDC-FM-INT-003-SHOULD | SHOULD | Support create interaction (POST {resourceType}) | POST |
| SDC-FM-INT-004-SHOULD | SHOULD | Support update interaction (PUT {resourceType}/{id}) | PUT |
| SDC-FM-INT-005-MAY | MAY | Support delete interaction (DELETE {resourceType}/{id}) | DELETE |
| SDC-FM-INT-006-MAY | MAY | Support vread interaction (GET {resourceType}/{id}/_history/{vid}) | GET |
| SDC-FM-INT-007-MAY | MAY | Support patch interaction (PATCH {resourceType}/{id}) | PATCH |

### HTTP Status Codes

| Req ID | Level | Description | Status Code |
|--------|-------|-------------|-------------|
| SDC-FM-INT-010-SHALL | SHALL | Return 200 OK for successful read | 200 |
| SDC-FM-INT-011-SHALL | SHALL | Return 201 Created for successful create | 201 |
| SDC-FM-INT-012-SHALL | SHALL | Return 404 Not Found for missing resource | 404 |
| SDC-FM-INT-013-SHALL | SHALL | Return 400 Bad Request for invalid syntax | 400 |
| SDC-FM-INT-014-SHALL | SHALL | Return 422 Unprocessable Entity for validation errors | 422 |
| SDC-FM-INT-015-SHOULD | SHOULD | Return 500 Internal Server Error for server failures | 500 |
| SDC-FM-INT-016-MAY | MAY | Return 429 Too Many Requests for rate limiting | 429 |
| SDC-FM-INT-017-MAY | MAY | Return 413 Payload Too Large for oversized requests | 413 |

### Content Negotiation

| Req ID | Level | Description | Header |
|--------|-------|-------------|--------|
| SDC-FM-INT-020-SHALL | SHALL | Support application/fhir+json content type | Accept: application/fhir+json |
| SDC-FM-INT-021-SHOULD | SHOULD | Support application/fhir+xml content type | Accept: application/fhir+xml |
| SDC-FM-INT-022-MAY | MAY | Support gzip compression | Accept-Encoding: gzip |

### Conditional Operations

| Req ID | Level | Description | Header |
|--------|-------|-------------|--------|
| SDC-FM-INT-030-MAY | MAY | Support conditional create (If-None-Exist) | If-None-Exist |
| SDC-FM-INT-031-MAY | MAY | Support conditional update (If-Match) | If-Match |
| SDC-FM-INT-032-MAY | MAY | Support conditional delete (If-Match) | If-Match |

---

## Security Requirements

### Authentication & Authorization

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-SEC-001-SHOULD | SHOULD | Support SMART on FHIR authentication | SMART App Launch |
| SDC-FM-SEC-002-SHOULD | SHOULD | Support OAuth 2.0 bearer tokens | RFC 6750 |
| SDC-FM-SEC-003-SHOULD | SHOULD | Validate user/Questionnaire.read scope | SMART Scopes |
| SDC-FM-SEC-004-SHOULD | SHOULD | Validate user/Questionnaire.write scope for create/update | SMART Scopes |
| SDC-FM-SEC-005-MAY | MAY | Support system/*.read scope for service accounts | SMART Scopes |

### Transport Security

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-SEC-010-SHALL | SHALL | Use HTTPS for all API endpoints in production | TLS 1.2+ |
| SDC-FM-SEC-011-SHOULD | SHOULD | Reject HTTP connections in production | Security Best Practice |

### Access Control

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-SEC-020-SHOULD | SHOULD | Implement resource-level access control | Security Framework |
| SDC-FM-SEC-021-MAY | MAY | Support compartment-based access control | FHIR Compartments |
| SDC-FM-SEC-022-MAY | MAY | Log all access attempts for audit | Audit Logging |

---

## Validation Requirements

### Resource Validation

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-VAL-001-SHALL | SHALL | Validate resources against FHIR R4 base schema | FHIR R4 Spec |
| SDC-FM-VAL-002-SHOULD | SHOULD | Validate Questionnaire against SDC profile | StructureDefinition/sdc-questionnaire |
| SDC-FM-VAL-003-MAY | MAY | Validate ValueSet compose structure | ValueSet Resource |
| SDC-FM-VAL-004-MAY | MAY | Validate canonical URL format | FHIR R4 Datatypes |

### Business Rules

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-VAL-010-SHALL | SHALL | Require Questionnaire.status field | Questionnaire.status |
| SDC-FM-VAL-011-SHOULD | SHOULD | Validate Questionnaire.item structure | Questionnaire.item |
| SDC-FM-VAL-012-MAY | MAY | Validate answerValueSet references | Questionnaire.item.answerValueSet |

---

## Performance Requirements

### Response Time

| Req ID | Level | Description | Target |
|--------|-------|-------------|--------|
| SDC-FM-PERF-001-SHOULD | SHOULD | Return read requests within 200ms (p95) | Performance |
| SDC-FM-PERF-002-SHOULD | SHOULD | Return search requests within 500ms (p95) | Performance |
| SDC-FM-PERF-003-MAY | MAY | Return $package requests within 2s (p95) | Performance |

### Scalability

| Req ID | Level | Description | Target |
|--------|-------|-------------|--------|
| SDC-FM-PERF-010-SHOULD | SHOULD | Support 100 concurrent requests | Scalability |
| SDC-FM-PERF-011-MAY | MAY | Support caching of frequently accessed resources | Caching |
| SDC-FM-PERF-012-MAY | MAY | Implement rate limiting to prevent abuse | Rate Limiting |

---

## Metadata Requirements

### CapabilityStatement

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-META-001-SHALL | SHALL | Publish CapabilityStatement at /metadata | FHIR R4 Spec |
| SDC-FM-META-002-SHALL | SHALL | Declare support for SDC Form Manager | CapabilityStatement.instantiates |
| SDC-FM-META-003-SHOULD | SHOULD | List supported Questionnaire profiles | CapabilityStatement.rest.resource.supportedProfile |
| SDC-FM-META-004-SHOULD | SHOULD | List supported operations | CapabilityStatement.rest.resource.operation |
| SDC-FM-META-005-SHOULD | SHOULD | List supported search parameters | CapabilityStatement.rest.resource.searchParam |

### Version Information

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-META-010-SHALL | SHALL | Declare FHIR version (4.0.1) | CapabilityStatement.fhirVersion |
| SDC-FM-META-011-SHOULD | SHOULD | Declare SDC IG version | CapabilityStatement.implementationGuide |
| SDC-FM-META-012-MAY | MAY | Provide software version | CapabilityStatement.software.version |

---

## Error Handling Requirements

### OperationOutcome Usage

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-ERR-001-SHALL | SHALL | Return OperationOutcome for all error responses | FHIR R4 OperationOutcome |
| SDC-FM-ERR-002-SHALL | SHALL | Include issue.severity (error/warning/information) | OperationOutcome.issue.severity |
| SDC-FM-ERR-003-SHALL | SHALL | Include issue.code (from IssueType value set) | OperationOutcome.issue.code |
| SDC-FM-ERR-004-SHOULD | SHOULD | Include issue.diagnostics with human-readable message | OperationOutcome.issue.diagnostics |
| SDC-FM-ERR-005-MAY | MAY | Include issue.expression pointing to problematic field | OperationOutcome.issue.expression |

### Error Scenarios

| Req ID | Level | Description | Status Code |
|--------|-------|-------------|-------------|
| SDC-FM-ERR-010-SHALL | SHALL | Handle resource not found gracefully | 404 |
| SDC-FM-ERR-011-SHALL | SHALL | Handle malformed JSON gracefully | 400 |
| SDC-FM-ERR-012-SHALL | SHALL | Handle validation errors gracefully | 422 |
| SDC-FM-ERR-013-SHOULD | SHOULD | Handle server errors gracefully | 500 |
| SDC-FM-ERR-014-MAY | MAY | Handle timeout errors gracefully | 504 |

---

## Testing Requirements

### Compliance Testing

| Req ID | Level | Description | Reference |
|--------|-------|-------------|-----------|
| SDC-FM-TEST-001-SHOULD | SHOULD | Pass Touchstone SDC Form Manager test suite | Touchstone |
| SDC-FM-TEST-002-SHOULD | SHOULD | Validate against SDC Questionnaire examples | SDC IG Examples |
| SDC-FM-TEST-003-MAY | MAY | Participate in FHIR Connectathon testing | FHIR Connectathon |

### Test Coverage

| Req ID | Level | Description | Target |
|--------|-------|-------------|--------|
| SDC-FM-TEST-010-SHOULD | SHOULD | Achieve 80%+ code coverage | Test Coverage |
| SDC-FM-TEST-011-SHOULD | SHOULD | Test all SHALL requirements | Requirement Coverage |
| SDC-FM-TEST-012-MAY | MAY | Test all SHOULD requirements | Requirement Coverage |

---

## Summary by Conformance Level

### SHALL Requirements (Mandatory)

**Total: 35 SHALL requirements**

**Categories:**
- Resource Support: 1
- Questionnaire: 8
- ValueSet Operations: 0
- $package Operation: 12
- Search Parameters: 6
- Interactions: 8

### SHOULD Requirements (Recommended)

**Total: 48 SHOULD requirements**

**Categories:**
- Resource Support: 2
- Questionnaire: 12
- ValueSet: 8
- CodeSystem: 2
- Operations: 8
- Performance: 3
- Security: 6
- Others: 7

### MAY Requirements (Optional)

**Total: 53 MAY requirements**

**Categories:**
- Resource Support: 3
- Questionnaire: 7
- ValueSet: 2
- CodeSystem: 2
- Library: 4
- Operations: 13
- Search: 10
- Security: 4
- Others: 8

---

## Implementation Checklist

### Phase 1: Core Functionality (SHALL Requirements)

- [ ] SDC-FM-RES-001-SHALL: Questionnaire resource support
- [ ] SDC-FM-Q-010-SHALL: Read Questionnaire
- [ ] SDC-FM-Q-011-SHALL: Search Questionnaire
- [ ] SDC-FM-Q-020-SHALL through Q-028-SHALL: Core search parameters
- [ ] SDC-FM-OP-PKG-001-SHALL through OP-PKG-015-SHALL: $package operation
- [ ] SDC-FM-INT-001-SHALL through INT-014-SHALL: HTTP interactions
- [ ] SDC-FM-SEC-010-SHALL: HTTPS in production
- [ ] SDC-FM-VAL-001-SHALL, VAL-010-SHALL: Resource validation
- [ ] SDC-FM-ERR-001-SHALL through ERR-005-SHALL: Error handling
- [ ] SDC-FM-META-001-SHALL through META-002-SHALL: CapabilityStatement

### Phase 2: Enhanced Functionality (SHOULD Requirements)

- [ ] SDC-FM-Q-012-SHOULD through Q-013-SHOULD: Create/Update Questionnaire
- [ ] SDC-FM-VS-010-SHOULD through VS-030-SHOULD: ValueSet support
- [ ] SDC-FM-CS-010-SHOULD through CS-020-SHOULD: CodeSystem support
- [ ] SDC-FM-OP-PKG-006-SHOULD through OP-PKG-009-SHOULD: Enhanced packaging
- [ ] SDC-FM-SEC-001-SHOULD through SEC-004-SHOULD: Authentication
- [ ] SDC-FM-PERF-001-SHOULD through PERF-010-SHOULD: Performance

### Phase 3: Optional Features (MAY Requirements)

- [ ] SDC-FM-LIB-010-MAY through LIB-021-MAY: Library support
- [ ] SDC-FM-OP-POP-001-MAY through OP-POP-004-MAY: $populate operation
- [ ] SDC-FM-OP-EXT-001-MAY through OP-EXT-003-MAY: $extract operation
- [ ] SDC-FM-OP-ASM-001-MAY through OP-ASM-002-MAY: $assemble operation
- [ ] Advanced search, caching, and optimization features

---

## Traceability Matrix

Use this format to map requirements to tests:

```markdown
| Requirement ID | Status | Test ID | Test Name | Result |
|----------------|--------|---------|-----------|--------|
| SDC-FM-OP-PKG-001-SHALL | ✅ Implemented | TEST-PKG-001 | test_package_by_id | PASS |
| SDC-FM-OP-PKG-008-SHALL | ✅ Implemented | TEST-PKG-008 | test_bundle_type_collection | PASS |
| SDC-FM-Q-020-SHALL | ✅ Implemented | TEST-Q-020 | test_search_by_id | PASS |
| SDC-FM-OP-PKG-016-MAY | ❌ Not Implemented | - | - | - |
```

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-23 | Initial requirements extraction from SDC CapabilityStatement |

---

**Document Status:** DRAFT

**Next Steps:**
1. Review and validate requirement IDs
2. Map existing tests to requirement IDs
3. Identify coverage gaps
4. Prioritize unimplemented SHALL requirements
