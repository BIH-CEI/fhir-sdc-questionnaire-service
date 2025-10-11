# SDC Form Manager - Requirements Specification

## Overview
A Form Manager implementing the FHIR Structured Data Capture (SDC) specification v4.0.0 for managing healthcare questionnaires and their dependencies.

**Specification Reference:** https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html

---

## 1. Core SDC Form Manager Capabilities

### 1.1 Required Resources (SHALL Support)

#### Questionnaire
- **Operations:** Read, Create, Update, Delete
- **Custom Operations:**
  - `$assemble` - Assemble modular questionnaires
  - `$package` - Generate bundle with Questionnaire + dependencies (ValueSets, CodeSystems, Libraries)
- **Search Parameters:**
  - `definition` - Search by definition URL
  - `code` - Search by questionnaire code
  - `combo-code` - Combined code search
  - `title` - Search by title (for autocomplete)
  - `status` - Filter by publication status

#### ValueSet
- **Operations:** Read, Create, Update
- **Search Parameters:**
  - `status` - Publication status
  - `reference` - Reference URL
  - `experimental` - Filter experimental value sets
  - `url` - Canonical URL

#### CodeSystem
- **Operations:** Read, Create, Update (SHOULD support)
- **Search Parameters:**
  - `status` - Publication status
  - `content-mode` - Content mode filter
  - `experimental` - Filter experimental code systems

### 1.2 Optional Resources (MAY Support)
- Library
- StructureMap
- StructureDefinition
- ConceptMap

---

## 2. FHIR Terminology Services

### 2.1 Required Operations

#### `ValueSet/$expand`
**Purpose:** Expand a ValueSet to retrieve all codes for data entry/validation

**Key Use Cases:**
- Populate dropdown lists in forms
- Enable code search/filtering with text parameter
- Support pagination for large value sets

**Parameters:**
- `url` - ValueSet canonical URL
- `filter` - Text filter for code search
- `offset` - Pagination offset
- `count` - Pagination limit
- `date` - Expansion evaluation date (optional)

**Response:**
- Expanded ValueSet with code list
- OR OperationOutcome (error: too-costly if expansion too large)

#### `ValueSet/$validate-code`
**Purpose:** Validate if a code exists in a ValueSet

**Parameters:**
- `url` - ValueSet URL
- `code` - Code to validate
- `system` - Code system
- `display` - Code display name (optional)

**Response:**
- Boolean result + validation details

#### `CodeSystem/$lookup`
**Purpose:** Retrieve details about a specific code

**Parameters:**
- `code` - Code value
- `system` - Code system URL
- `property` - Specific properties to return (optional)

**Response:**
- Code details (display, properties, relationships)

### 2.2 Additional Terminology Operations (Optional)
- `$subsumes` - Test hierarchical relationships between codes
- `$translate` - Convert concepts between code systems using ConceptMaps

---

## 3. Questionnaire Bundle/Package API

### 3.1 Bundle Composition
When requesting a Questionnaire bundle, return a FHIR Bundle containing:

**Primary Resource:**
- Questionnaire resource

**Dependencies (included automatically):**
- All referenced ValueSets (from answerValueSet bindings)
- All referenced CodeSystems (used by ValueSets)
- All referenced Libraries (for calculated expressions, FHIRPath)
- Related StructureMaps (if form uses data extraction)

### 3.2 API Endpoint Design
```
GET /Questionnaire/{id}/$package
POST /Questionnaire/$package (with Questionnaire in body)
```

**Response:**
- FHIR Bundle (type: collection)
- All dependencies resolved and included

### 3.3 Dependency Resolution
- Traverse Questionnaire.item.answerValueSet references
- Resolve ValueSet.compose.include references to CodeSystems
- Include Library references from extensions (cqf-library)
- Include StructureMap if specified in Questionnaire.extension

---

## 4. Search & Discovery Features

### 4.1 Dynamic Autocomplete Search
**Requirement:** Type-ahead search for Questionnaires as user types

**Implementation:**
- Debounced API calls (300ms delay)
- Search across: title, name, description, publisher
- Return metadata: id, title, version, status, date
- Sub-100ms response time target

**Search Endpoint:**
```
GET /Questionnaire?title:contains={query}&_summary=true
GET /Questionnaire?_content={query}&_summary=true
```

### 4.2 Metadata Filters
- Status (draft, active, retired)
- Publisher
- Date range (last modified)
- Version
- Experimental flag

---

## 5. Technology Stack (Proposed)

### 5.1 Backend
- **HAPI FHIR Server** (Docker) - FHIR-compliant storage, search, terminology services
- **PostgreSQL** - Primary database with full-text search
- **Python FastAPI** - Custom business logic layer for:
  - Bundle/package generation
  - Enhanced search endpoints
  - Terminology service extensions
  - Custom SDC operations

### 5.2 Frontend
- **React/TypeScript** - UI for form management
- **Debounced search** - Autocomplete with 300ms delay
- **FHIR client library** - `fhirpath.js` for expression evaluation

### 5.3 Optional Enhancements
- **Redis** - Cache frequently accessed ValueSets/CodeSystems
- **Elasticsearch** - Advanced search if >10k Questionnaires (future)

---

## 6. API Requirements Summary

### 6.1 CRUD Operations
```
GET    /Questionnaire/{id}           # Read
POST   /Questionnaire                # Create
PUT    /Questionnaire/{id}           # Update
DELETE /Questionnaire/{id}           # Delete

GET    /ValueSet/{id}                # Read
POST   /ValueSet                     # Create
PUT    /ValueSet/{id}                # Update

GET    /CodeSystem/{id}              # Read
POST   /CodeSystem                   # Create
PUT    /CodeSystem/{id}              # Update
```

### 6.2 Search Operations
```
GET /Questionnaire?title:contains={text}
GET /Questionnaire?status=active
GET /Questionnaire?_content={text}

GET /ValueSet?status=active
GET /CodeSystem?status=active
```

### 6.3 Terminology Services
```
GET /ValueSet/$expand?url={url}&filter={text}&count=50
GET /ValueSet/{id}/$expand?filter={text}
POST /ValueSet/$expand (with ValueSet in body)

GET /ValueSet/$validate-code?url={url}&code={code}&system={system}
POST /ValueSet/$validate-code (with parameters in body)

GET /CodeSystem/$lookup?code={code}&system={system}
```

### 6.4 Custom SDC Operations
```
GET /Questionnaire/{id}/$package     # Get bundle with dependencies
POST /Questionnaire/$package         # Package provided Questionnaire

GET /Questionnaire/{id}/$assemble    # Assemble modular questionnaire
```

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Search response: < 100ms (for <10k Questionnaires)
- ValueSet expansion: < 500ms (for <5k codes)
- Bundle generation: < 1s (with up to 20 dependencies)

### 7.2 Security
- Meet FHIR security requirements (OAuth 2.0 / SMART on FHIR)
- Role-based access control (RBAC)
- Audit logging for create/update/delete operations

### 7.3 Data Formats
- Support JSON and XML (FHIR R4/R5)
- UTF-8 encoding
- FHIR validation on create/update

### 7.4 Scalability
- Support 10,000+ Questionnaires
- 100+ concurrent users
- Horizontal scaling capability (stateless API layer)

---

## 8. Implementation Phases

### Phase 1: Foundation
- [ ] Set up HAPI FHIR server with PostgreSQL (Docker)
- [ ] Implement basic CRUD for Questionnaire, ValueSet, CodeSystem
- [ ] Basic search functionality

### Phase 2: Terminology Services
- [ ] Implement ValueSet `$expand` operation
- [ ] Implement ValueSet `$validate-code` operation
- [ ] Implement CodeSystem `$lookup` operation
- [ ] Add caching for frequent expansions

### Phase 3: Bundle/Package API
- [ ] Implement Questionnaire `$package` operation
- [ ] Dependency resolution algorithm
- [ ] Bundle generation with all related resources

### Phase 4: Search & UI
- [ ] FastAPI layer for enhanced search
- [ ] Dynamic autocomplete endpoint
- [ ] React frontend with search interface
- [ ] Form metadata viewer

### Phase 5: Advanced Features
- [ ] Implement `$assemble` operation for modular questionnaires
- [ ] Add `$translate` for ConceptMap support
- [ ] Elasticsearch integration (if needed)
- [ ] Advanced filtering and faceted search

---

## 9. Standards Compliance

- **FHIR Version:** R4 (4.0.1) / R5 (5.0.0)
- **SDC IG Version:** 4.0.0 (October 2025)
- **Capability Statement:** sdc-form-manager
- **Must support:** Questionnaire, ValueSet (SHALL)
- **Should support:** CodeSystem
- **May support:** Library, StructureMap, StructureDefinition, ConceptMap

---

## 10. References

- SDC Form Manager Capability Statement: https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html
- FHIR Terminology Services: https://build.fhir.org/terminology-service.html
- ValueSet $expand: https://build.fhir.org/valueset-operation-expand.html
- SDC Implementation Guide: https://build.fhir.org/ig/HL7/sdc/
- HAPI FHIR Documentation: https://hapifhir.io/

---

**Document Version:** 1.0
**Last Updated:** 2025-10-10
**Author:** Form Manager Development Team
