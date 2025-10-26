# Test-to-Requirement Mapping

**Purpose:** Map all SDC Form Manager requirements to test cases

**Total Requirements:** 136 (35 SHALL, 48 SHOULD, 53 MAY)

**Current Test Coverage:** 35/136 (25.7%)

**Last Updated:** 2025-10-23

---

## Coverage Summary

| Conformance Level | Total | Covered | Not Covered | Coverage % |
|-------------------|-------|---------|-------------|------------|
| SHALL (Mandatory) | 35 | 20 | 15 | 57.1% |
| SHOULD (Recommended) | 48 | 12 | 36 | 25.0% |
| MAY (Optional) | 53 | 3 | 50 | 5.7% |
| **TOTAL** | **136** | **35** | **101** | **25.7%** |

---

## Requirement Coverage Status

### ✅ = Covered by existing tests
### 🟡 = Partially covered
### ❌ = Not covered
### 🔵 = Not applicable (infrastructure/deployment)

---

## Resource Support Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-RES-001-SHALL | SHALL | ✅ | TEST-CRUD-001 | test_create_questionnaire_success |
| SDC-FM-RES-002-SHOULD | SHOULD | ❌ | - | (ValueSet support - not tested) |
| SDC-FM-RES-003-SHOULD | SHOULD | ❌ | - | (CodeSystem support - not tested) |
| SDC-FM-RES-004-MAY | MAY | ❌ | - | (Library support - not tested) |
| SDC-FM-RES-005-MAY | MAY | ❌ | - | (StructureMap support - not tested) |
| SDC-FM-RES-006-MAY | MAY | ❌ | - | (QuestionnaireResponse support - not tested) |

**Coverage: 1/6 (16.7%)**

---

## Questionnaire Requirements

### Profile Support

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-Q-001-SHALL | SHALL | 🟡 | TEST-CRUD-001 | (Basic Questionnaire tested, not SDC profile) |
| SDC-FM-Q-002-SHOULD | SHOULD | ❌ | - | (Advanced Rendering profile - not tested) |
| SDC-FM-Q-003-SHOULD | SHOULD | ❌ | - | (Adaptive Questionnaire profile - not tested) |

### Interactions

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-Q-010-SHALL | SHALL | ✅ | TEST-CRUD-010 | test_get_questionnaire_success |
| SDC-FM-Q-011-SHALL | SHALL | ✅ | TEST-SEARCH-001 | test_search_questionnaires_by_status |
| SDC-FM-Q-012-SHOULD | SHOULD | ✅ | TEST-CRUD-001 | test_create_questionnaire_success |
| SDC-FM-Q-013-SHOULD | SHOULD | ✅ | TEST-CRUD-020 | test_update_questionnaire_success |
| SDC-FM-Q-014-MAY | MAY | ✅ | TEST-CRUD-030 | test_delete_questionnaire_success |
| SDC-FM-Q-015-MAY | MAY | ❌ | - | (vread - not tested) |
| SDC-FM-Q-016-MAY | MAY | ❌ | - | (history-instance - not tested) |

### Search Parameters

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-Q-020-SHALL | SHALL | ✅ | TEST-CRUD-010 | test_get_questionnaire_success (implicit _id) |
| SDC-FM-Q-021-SHALL | SHALL | 🟡 | TEST-PKG-009 | test_canonical_url_resolution (partial) |
| SDC-FM-Q-022-SHALL | SHALL | 🟡 | TEST-PKG-010 | test_version_specific_canonical_resolution (partial) |
| SDC-FM-Q-023-SHALL | SHALL | ✅ | TEST-SEARCH-001 | test_search_questionnaires_by_status |
| SDC-FM-Q-024-SHOULD | SHOULD | ✅ | TEST-SEARCH-002 | test_search_questionnaires_by_title |
| SDC-FM-Q-025-SHOULD | SHOULD | ❌ | - | (search by name - not tested) |
| SDC-FM-Q-026-SHOULD | SHOULD | ❌ | - | (search by publisher - not tested) |
| SDC-FM-Q-027-SHOULD | SHOULD | ❌ | - | (search by date - not tested) |
| SDC-FM-Q-028-SHOULD | SHOULD | ❌ | - | (search by _lastUpdated - not tested) |
| SDC-FM-Q-029-MAY | MAY | ❌ | - | (search by identifier - not tested) |
| SDC-FM-Q-030-MAY | MAY | ❌ | - | (search by subject-type - not tested) |
| SDC-FM-Q-031-MAY | MAY | ❌ | - | (search by context - not tested) |
| SDC-FM-Q-032-MAY | MAY | ❌ | - | (search by definition - not tested) |

### Search Modifiers

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-Q-040-SHOULD | SHOULD | ❌ | - | (title:contains - not tested) |
| SDC-FM-Q-041-SHOULD | SHOULD | ❌ | - | (name:contains - not tested) |
| SDC-FM-Q-042-MAY | MAY | ❌ | - | (:exact modifier - not tested) |

### Search Combinations

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-Q-050-SHALL | SHALL | ✅ | TEST-PKG-010 | test_version_specific_canonical_resolution |
| SDC-FM-Q-051-SHOULD | SHOULD | ❌ | - | (status + _sort - not tested) |
| SDC-FM-Q-052-MAY | MAY | ❌ | - | (_revinclude - not tested) |

**Questionnaire Coverage: 11/23 (47.8%)**

---

## $package Operation Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-OP-PKG-001-SHALL | SHALL | ✅ | TEST-PKG-001 | test_instance_level_endpoint |
| SDC-FM-OP-PKG-002-SHALL | SHALL | ✅ | TEST-PKG-002 | test_type_level_post_endpoint |
| SDC-FM-OP-PKG-003-SHALL | SHALL | ✅ | TEST-PKG-001 | test_package_returns_collection_bundle |
| SDC-FM-OP-PKG-004-SHALL | SHALL | ✅ | TEST-PKG-003 | test_includes_referenced_valuesets |
| SDC-FM-OP-PKG-005-SHALL | SHALL | ✅ | TEST-PKG-004 | test_includes_referenced_codesystems |
| SDC-FM-OP-PKG-006-SHOULD | SHOULD | ✅ | TEST-LIB-001 | test_includes_library_references |
| SDC-FM-OP-PKG-007-SHOULD | SHOULD | ❌ | - | (StructureMap inclusion - not tested) |
| SDC-FM-OP-PKG-008-SHALL | SHALL | ✅ | TEST-PKG-001 | test_package_returns_collection_bundle |
| SDC-FM-OP-PKG-009-SHOULD | SHOULD | ✅ | TEST-PKG-002 | test_questionnaire_is_first_entry |
| SDC-FM-OP-PKG-010-SHALL | SHALL | ✅ | TEST-PKG-006 | test_supports_include_dependencies_parameter |
| SDC-FM-OP-PKG-011-SHALL | SHALL | ✅ | TEST-PKG-009 | test_canonical_url_resolution |
| SDC-FM-OP-PKG-012-SHALL | SHALL | ✅ | TEST-PKG-010 | test_version_specific_canonical_resolution |
| SDC-FM-OP-PKG-013-SHOULD | SHOULD | ✅ | TEST-PKG-005 | test_missing_dependency_returns_operation_outcome |
| SDC-FM-OP-PKG-014-SHOULD | SHOULD | 🟡 | - | (Circular dependency - implicit in resolver, not explicit test) |
| SDC-FM-OP-PKG-015-SHALL | SHALL | ✅ | TEST-PKG-014 | test_questionnaire_not_found_returns_404 |
| SDC-FM-OP-PKG-016-MAY | MAY | ✅ | TEST-PKG-009 | test_canonical_url_resolution |
| SDC-FM-OP-PKG-017-MAY | MAY | ✅ | TEST-PKG-010 | test_version_specific_canonical_resolution |
| SDC-FM-OP-PKG-018-SHOULD | SHOULD | ✅ | TEST-PKG-013 | test_bundle_has_sdc_tags |
| SDC-FM-OP-PKG-019-MAY | MAY | ❌ | - | (CodeSystem subsetting - not tested) |
| SDC-FM-OP-PKG-020-MAY | MAY | ❌ | - | (Caching - not tested) |

**$package Coverage: 16/20 (80.0%)**

---

## ValueSet Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-VS-010-SHOULD | SHOULD | ❌ | - | (read ValueSet - not tested) |
| SDC-FM-VS-011-SHOULD | SHOULD | ❌ | - | (search ValueSet - not tested) |
| SDC-FM-VS-012-MAY | MAY | ❌ | - | (create ValueSet - not tested) |
| SDC-FM-VS-013-MAY | MAY | ❌ | - | (update ValueSet - not tested) |
| SDC-FM-VS-020-SHOULD | SHOULD | ❌ | - | (search ValueSet by _id - not tested) |
| SDC-FM-VS-021-SHOULD | SHOULD | ❌ | - | (search ValueSet by url - not tested) |
| SDC-FM-VS-022-SHOULD | SHOULD | ❌ | - | (search ValueSet by version - not tested) |
| SDC-FM-VS-023-SHOULD | SHOULD | ❌ | - | (search ValueSet by status - not tested) |
| SDC-FM-VS-024-MAY | MAY | ❌ | - | (search ValueSet by title - not tested) |
| SDC-FM-VS-030-SHOULD | SHOULD | ❌ | - | ($expand operation - not tested) |
| SDC-FM-VS-031-MAY | MAY | ❌ | - | ($validate-code operation - not tested) |

**ValueSet Coverage: 0/11 (0%)**

---

## CodeSystem Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-CS-010-SHOULD | SHOULD | ❌ | - | (read CodeSystem - not tested) |
| SDC-FM-CS-011-MAY | MAY | ❌ | - | (search CodeSystem - not tested) |
| SDC-FM-CS-020-SHOULD | SHOULD | ❌ | - | (search CodeSystem by url - not tested) |
| SDC-FM-CS-021-MAY | MAY | ❌ | - | (search CodeSystem by version - not tested) |
| SDC-FM-CS-030-MAY | MAY | ❌ | - | ($lookup operation - not tested) |

**CodeSystem Coverage: 0/5 (0%)**

---

## Library Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-LIB-010-MAY | MAY | ❌ | - | (read Library - not tested) |
| SDC-FM-LIB-011-MAY | MAY | ❌ | - | (search Library - not tested) |
| SDC-FM-LIB-020-MAY | MAY | ❌ | - | (search Library by url - not tested) |
| SDC-FM-LIB-021-MAY | MAY | ❌ | - | (search Library by version - not tested) |

**Library Coverage: 0/4 (0%)**

---

## Other Operations

### $populate (Optional)

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-OP-POP-001-MAY | MAY | ❌ | - | ($populate support - not implemented) |
| SDC-FM-OP-POP-002-MAY | MAY | ❌ | - | ($populate subject parameter - not implemented) |
| SDC-FM-OP-POP-003-MAY | MAY | ❌ | - | ($populate pre-fill - not implemented) |
| SDC-FM-OP-POP-004-MAY | MAY | ❌ | - | ($populate CQL execution - not implemented) |

### $extract (Optional)

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-OP-EXT-001-MAY | MAY | ❌ | - | ($extract support - not implemented) |
| SDC-FM-OP-EXT-002-MAY | MAY | ❌ | - | ($extract resource extraction - not implemented) |
| SDC-FM-OP-EXT-003-MAY | MAY | ❌ | - | ($extract StructureMap - not implemented) |

### $assemble (Optional)

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-OP-ASM-001-MAY | MAY | ❌ | - | ($assemble support - not implemented) |
| SDC-FM-OP-ASM-002-MAY | MAY | ❌ | - | ($assemble modular composition - not implemented) |

**Other Operations Coverage: 0/11 (0%)**

---

## Search Parameter Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-SP-001-SHALL | SHALL | ✅ | TEST-CRUD-010 | test_get_questionnaire_success |
| SDC-FM-SP-002-SHALL | SHALL | ❌ | - | (_lastUpdated search - not tested) |
| SDC-FM-SP-003-SHOULD | SHOULD | ❌ | - | (_sort parameter - not tested) |
| SDC-FM-SP-004-SHOULD | SHOULD | ✅ | TEST-SEARCH-003 | test_search_questionnaires_with_count_limit |
| SDC-FM-SP-005-MAY | MAY | ❌ | - | (_summary parameter - not tested) |
| SDC-FM-SP-006-MAY | MAY | ❌ | - | (_elements parameter - not tested) |
| SDC-FM-SP-007-MAY | MAY | ❌ | - | (_include parameter - not tested) |
| SDC-FM-SP-008-MAY | MAY | ❌ | - | (_revinclude parameter - not tested) |
| SDC-FM-SP-010-SHOULD | SHOULD | ❌ | - | (date comparators - not tested) |
| SDC-FM-SP-011-MAY | MAY | ❌ | - | (string modifiers - not tested) |

**Search Parameter Coverage: 2/10 (20%)**

---

## Interaction Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-INT-001-SHALL | SHALL | ✅ | TEST-CRUD-010 | test_get_questionnaire_success |
| SDC-FM-INT-002-SHALL | SHALL | ✅ | TEST-SEARCH-001 | test_search_questionnaires_by_status |
| SDC-FM-INT-003-SHOULD | SHOULD | ✅ | TEST-CRUD-001 | test_create_questionnaire_success |
| SDC-FM-INT-004-SHOULD | SHOULD | ✅ | TEST-CRUD-020 | test_update_questionnaire_success |
| SDC-FM-INT-005-MAY | MAY | ✅ | TEST-CRUD-030 | test_delete_questionnaire_success |
| SDC-FM-INT-006-MAY | MAY | ❌ | - | (vread - not tested) |
| SDC-FM-INT-007-MAY | MAY | ❌ | - | (patch - not tested) |

### HTTP Status Codes

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-INT-010-SHALL | SHALL | ✅ | TEST-CRUD-010 | test_get_questionnaire_success |
| SDC-FM-INT-011-SHALL | SHALL | ✅ | TEST-CRUD-001 | test_create_questionnaire_success |
| SDC-FM-INT-012-SHALL | SHALL | ✅ | TEST-CRUD-011 | test_get_questionnaire_not_found_returns_404 |
| SDC-FM-INT-013-SHALL | SHALL | ✅ | TEST-CRUD-002 | test_create_questionnaire_invalid_type_returns_400 |
| SDC-FM-INT-014-SHALL | SHALL | ✅ | TEST-CRUD-003 | test_create_questionnaire_missing_required_field |
| SDC-FM-INT-015-SHOULD | SHOULD | ✅ | TEST-CRUD-012 | test_get_questionnaire_hapi_unreachable |
| SDC-FM-INT-016-MAY | MAY | ❌ | - | (429 rate limiting - not tested) |
| SDC-FM-INT-017-MAY | MAY | ❌ | - | (413 payload too large - not tested) |

### Content Negotiation

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-INT-020-SHALL | SHALL | 🔵 | - | (JSON support - infrastructure concern) |
| SDC-FM-INT-021-SHOULD | SHOULD | ❌ | - | (XML support - not tested) |
| SDC-FM-INT-022-MAY | MAY | ❌ | - | (gzip compression - not tested) |

### Conditional Operations

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-INT-030-MAY | MAY | ❌ | - | (If-None-Exist - not tested) |
| SDC-FM-INT-031-MAY | MAY | ❌ | - | (If-Match update - not tested) |
| SDC-FM-INT-032-MAY | MAY | ❌ | - | (If-Match delete - not tested) |

**Interaction Coverage: 12/20 (60%)**

---

## Security Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-SEC-001-SHOULD | SHOULD | ❌ | - | (SMART on FHIR - not tested) |
| SDC-FM-SEC-002-SHOULD | SHOULD | ❌ | - | (OAuth 2.0 - not tested) |
| SDC-FM-SEC-003-SHOULD | SHOULD | ❌ | - | (read scope validation - not tested) |
| SDC-FM-SEC-004-SHOULD | SHOULD | ❌ | - | (write scope validation - not tested) |
| SDC-FM-SEC-005-MAY | MAY | ❌ | - | (system/*.read scope - not tested) |
| SDC-FM-SEC-010-SHALL | SHALL | 🔵 | - | (HTTPS in production - deployment concern) |
| SDC-FM-SEC-011-SHOULD | SHOULD | 🔵 | - | (Reject HTTP - deployment concern) |
| SDC-FM-SEC-020-SHOULD | SHOULD | ❌ | - | (Resource-level access control - not tested) |
| SDC-FM-SEC-021-MAY | MAY | ❌ | - | (Compartment access control - not tested) |
| SDC-FM-SEC-022-MAY | MAY | ❌ | - | (Audit logging - not tested) |

**Security Coverage: 0/10 (0%)** (excluding deployment concerns)

---

## Validation Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-VAL-001-SHALL | SHALL | ✅ | TEST-CRUD-003 | test_create_questionnaire_missing_required_field |
| SDC-FM-VAL-002-SHOULD | SHOULD | ❌ | - | (SDC profile validation - not tested) |
| SDC-FM-VAL-003-MAY | MAY | ❌ | - | (ValueSet compose validation - not tested) |
| SDC-FM-VAL-004-MAY | MAY | ❌ | - | (Canonical URL format validation - not tested) |
| SDC-FM-VAL-010-SHALL | SHALL | ✅ | TEST-CRUD-003 | test_create_questionnaire_missing_required_field |
| SDC-FM-VAL-011-SHOULD | SHOULD | ❌ | - | (Item structure validation - not tested) |
| SDC-FM-VAL-012-MAY | MAY | ❌ | - | (answerValueSet validation - not tested) |

**Validation Coverage: 2/7 (28.6%)**

---

## Performance Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-PERF-001-SHOULD | SHOULD | ❌ | - | (Read < 200ms p95 - not tested) |
| SDC-FM-PERF-002-SHOULD | SHOULD | ❌ | - | (Search < 500ms p95 - not tested) |
| SDC-FM-PERF-003-MAY | MAY | ❌ | - | ($package < 2s p95 - not tested) |
| SDC-FM-PERF-010-SHOULD | SHOULD | ❌ | - | (100 concurrent requests - not tested) |
| SDC-FM-PERF-011-MAY | MAY | ❌ | - | (Caching - not tested) |
| SDC-FM-PERF-012-MAY | MAY | ❌ | - | (Rate limiting - not tested) |

**Performance Coverage: 0/6 (0%)**

---

## Metadata Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-META-001-SHALL | SHALL | ❌ | - | (CapabilityStatement at /metadata - not tested) |
| SDC-FM-META-002-SHALL | SHALL | ❌ | - | (Declare SDC Form Manager - not tested) |
| SDC-FM-META-003-SHOULD | SHOULD | ❌ | - | (List supported profiles - not tested) |
| SDC-FM-META-004-SHOULD | SHOULD | ❌ | - | (List supported operations - not tested) |
| SDC-FM-META-005-SHOULD | SHOULD | ❌ | - | (List supported search parameters - not tested) |
| SDC-FM-META-010-SHALL | SHALL | ❌ | - | (Declare FHIR version - not tested) |
| SDC-FM-META-011-SHOULD | SHOULD | ❌ | - | (Declare SDC IG version - not tested) |
| SDC-FM-META-012-MAY | MAY | ❌ | - | (Software version - not tested) |

**Metadata Coverage: 0/8 (0%)**

---

## Error Handling Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-ERR-001-SHALL | SHALL | ✅ | TEST-CRUD-011 | test_get_questionnaire_not_found_returns_404 |
| SDC-FM-ERR-002-SHALL | SHALL | ❌ | - | (OperationOutcome.issue.severity - not explicitly tested) |
| SDC-FM-ERR-003-SHALL | SHALL | ❌ | - | (OperationOutcome.issue.code - not explicitly tested) |
| SDC-FM-ERR-004-SHOULD | SHOULD | ❌ | - | (OperationOutcome.issue.diagnostics - not explicitly tested) |
| SDC-FM-ERR-005-MAY | MAY | ❌ | - | (OperationOutcome.issue.expression - not explicitly tested) |
| SDC-FM-ERR-010-SHALL | SHALL | ✅ | TEST-CRUD-011 | test_get_questionnaire_not_found_returns_404 |
| SDC-FM-ERR-011-SHALL | SHALL | ✅ | TEST-FAIL-001 | test_malformed_json_returns_400 |
| SDC-FM-ERR-012-SHALL | SHALL | ✅ | TEST-CRUD-003 | test_create_questionnaire_missing_required_field |
| SDC-FM-ERR-013-SHOULD | SHOULD | ✅ | TEST-CRUD-012 | test_get_questionnaire_hapi_unreachable |
| SDC-FM-ERR-014-MAY | MAY | ❌ | - | (Timeout errors - not tested) |

**Error Handling Coverage: 5/10 (50%)**

---

## Testing Requirements

| Req ID | Level | Status | Test ID | Test Name |
|--------|-------|--------|---------|-----------|
| SDC-FM-TEST-001-SHOULD | SHOULD | ❌ | - | (Touchstone test suite - not run) |
| SDC-FM-TEST-002-SHOULD | SHOULD | 🟡 | - | (SDC examples - partial validation) |
| SDC-FM-TEST-003-MAY | MAY | ❌ | - | (FHIR Connectathon - not participated) |
| SDC-FM-TEST-010-SHOULD | SHOULD | ❌ | - | (80%+ code coverage - TBD) |
| SDC-FM-TEST-011-SHOULD | SHOULD | 🟡 | - | (Test all SHALL - 20/35 covered) |
| SDC-FM-TEST-012-MAY | MAY | 🟡 | - | (Test all SHOULD - 12/48 covered) |

**Testing Coverage: 0/6 (0%)** (meta-requirements)

---

## Priority Test Development

### Phase 1: Critical SHALL Requirements (15 tests needed)

Missing SHALL requirements that MUST be tested:

1. **SDC-FM-Q-021-SHALL** - Search by canonical URL
2. **SDC-FM-Q-022-SHALL** - Search by version
3. **SDC-FM-SP-002-SHALL** - Search by _lastUpdated
4. **SDC-FM-OP-PKG-014-SHOULD** - Explicit circular dependency test
5. **SDC-FM-META-001-SHALL** - CapabilityStatement endpoint
6. **SDC-FM-META-002-SHALL** - Declare SDC Form Manager
7. **SDC-FM-META-010-SHALL** - Declare FHIR version
8. **SDC-FM-ERR-002-SHALL** - OperationOutcome severity validation
9. **SDC-FM-ERR-003-SHALL** - OperationOutcome code validation

### Phase 2: Important SHOULD Requirements (36 tests needed)

Focus on functionality that enhances usability:

1. **ValueSet support** (11 tests) - SDC-FM-VS-*
2. **CodeSystem support** (5 tests) - SDC-FM-CS-*
3. **Search modifiers** (3 tests) - SDC-FM-Q-040/041/042
4. **Performance testing** (6 tests) - SDC-FM-PERF-*
5. **Security** (8 tests) - SDC-FM-SEC-*
6. **Metadata** (5 tests) - SDC-FM-META-*

### Phase 3: Optional MAY Requirements (50 tests possible)

Nice-to-have features:

1. **Library support** (4 tests)
2. **$populate operation** (4 tests)
3. **$extract operation** (3 tests)
4. **$assemble operation** (2 tests)
5. **Advanced search** (10+ tests)
6. **Conditional operations** (3 tests)

---

## Test File Organization

### Proposed Structure

```
tests/
├── sdc_compliance/
│   ├── test_package_operation.py          # ✅ Exists (16 tests)
│   ├── test_localize_operation.py          # ❌ NEW - $localize tests
│   ├── test_questionnaire_search.py        # ❌ NEW - Search parameter tests
│   ├── test_questionnaire_profiles.py      # ❌ NEW - SDC profile validation
│   └── test_metadata.py                    # ❌ NEW - CapabilityStatement tests
├── integration/
│   ├── test_questionnaire_crud.py          # ✅ Exists (18 tests)
│   ├── test_valueset_operations.py         # ❌ NEW - ValueSet CRUD
│   ├── test_codesystem_operations.py       # ❌ NEW - CodeSystem read/search
│   ├── test_library_operations.py          # ❌ NEW - Library support
│   └── test_search_parameters.py           # ❌ NEW - Advanced search
├── security/
│   ├── test_authentication.py              # ❌ NEW - OAuth/SMART tests
│   ├── test_authorization.py               # ❌ NEW - Scope validation
│   └── test_access_control.py              # ❌ NEW - Resource-level ACL
├── performance/
│   ├── test_response_times.py              # ❌ NEW - Latency tests
│   ├── test_concurrent_requests.py         # ❌ NEW - Load testing
│   └── test_caching.py                     # ❌ NEW - Cache validation
└── error_handling/
    ├── test_operation_outcome.py           # ❌ NEW - OperationOutcome structure
    ├── test_http_status_codes.py           # ❌ NEW - Status code validation
    └── test_edge_cases.py                  # ❌ NEW - Edge case handling
```

---

## Next Steps

### Option 1: Comprehensive Implementation (All 101 missing tests)
Implement all missing tests across all conformance levels

**Effort:** ~40-60 hours
**Benefit:** 100% requirement coverage

### Option 2: Phased Implementation

**Phase 1 (HIGH PRIORITY):** SHALL requirements only (15 tests)
**Effort:** ~8-12 hours
**Benefit:** 100% SHALL coverage (mandatory compliance)

**Phase 2 (MEDIUM PRIORITY):** SHOULD requirements (36 tests)
**Effort:** ~20-30 hours
**Benefit:** Best practice compliance

**Phase 3 (LOW PRIORITY):** MAY requirements (50 tests)
**Effort:** ~30-40 hours
**Benefit:** Complete feature set

### Option 3: Targeted Implementation
Focus on specific categories based on business priorities:
- ValueSet/CodeSystem support (16 tests)
- Metadata/CapabilityStatement (8 tests)
- Search enhancements (15 tests)
- Performance validation (6 tests)

---

## Recommendation

**Start with Phase 1:** Implement the 15 missing SHALL requirements first.

This ensures mandatory SDC compliance and provides the foundation for certification/validation.

**Rationale:**
- SHALL requirements are non-negotiable for SDC conformance
- Quickest path to baseline compliance
- Can then prioritize SHOULD/MAY based on user needs

---

**Would you like me to proceed with implementing Phase 1 (15 SHALL requirement tests)?**
