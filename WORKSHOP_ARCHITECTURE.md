# Multi-Site PROMIS Exchange: Technical Architecture

**Workshop for Technical & Product Managers**
**Focus:** Distributed PROM systems, terminology services, and integration challenges

---

## 1. Overview

This architecture demonstrates a realistic multi-site Patient-Reported Outcome Measures (PROM) exchange system using FHIR, with focus on:

- Distributed FHIR servers (Sites A & B)
- Centralized terminology services
- Version management challenges
- Translation/multilingual support
- Scoring integration
- Product/API gaps

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Workshop Demo Network                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────────┐        ┌──────────────────────────┐  │
│  │   Site A (Collection)    │        │   Site B (Review)        │  │
│  │  German Hospital         │        │   Multi-site Clinic      │  │
│  ├──────────────────────────┤        ├──────────────────────────┤  │
│  │ HAPI FHIR Server         │        │ HAPI FHIR Server         │  │
│  │ - Port: 8081             │        │ - Port: 8082             │  │
│  │ - MII PRO package v1.0   │◀──────▶│ - MII PRO package v2.0   │  │
│  │ - PROMIS scoring (CQL)   │        │ - Validation enabled     │  │
│  │ - Language: de-DE        │        │ - Language: de-DE, en-US │  │
│  └───────────┬──────────────┘        └───────────┬──────────────┘  │
│              │                                    │                  │
│              │ Terminology Lookups                │                  │
│              │ - ValueSet/$expand                 │                  │
│              │ - Multi-language                   │                  │
│              └────────────┬───────────────────────┘                  │
│                           ▼                                          │
│         ┌────────────────────────────────────────────────┐          │
│         │      Terminology Service (Port 3000)           │          │
│         ├────────────────────────────────────────────────┤          │
│         │  ┌─────────────────────────────────────┐       │          │
│         │  │  Enhanced Wrapper (FastAPI)         │       │          │
│         │  │  - LOINC Panel API (NEW)            │       │          │
│         │  │  - Ordinal values API (NEW)         │       │          │
│         │  │  - PROMIS scoring API (NEW)         │       │          │
│         │  │  - Multi-language support           │       │          │
│         │  └──────────────┬──────────────────────┘       │          │
│         │                 ▼                               │          │
│         │  ┌─────────────────────────────────────┐       │          │
│         │  │  ONTOSERVER (Base)                  │       │          │
│         │  │  - Standard FHIR terminology ops    │       │          │
│         │  │  - ValueSet/$expand                 │       │          │
│         │  │  - CodeSystem/$lookup               │       │          │
│         │  └─────────────────────────────────────┘       │          │
│         └────────────────────────────────────────────────┘          │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Demo UI / API (Port 8000)                        │  │
│  │  - Scenario triggers                                          │  │
│  │  - Side-by-side comparison                                    │  │
│  │  - API call visualization                                     │  │
│  │  - Problem injection                                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Specifications

### 3.1 Site A (Collection Site) - HAPI FHIR

**Purpose:** Data collection site using PROMIS questionnaires

**Configuration:**
- **Port:** 8081
- **Package:** `de.medizininformatikinitiative.kerndatensatz.pros:2026.0.0-rc.1`
- **PROMIS Version:** 1.0 (older scoring algorithm)
- **Language:** German (de-DE) default
- **CQL Engine:** Enabled (local scoring)
- **Terminology Server:** http://terminology-proxy:3000/fhir

**Capabilities:**
- Create/Store QuestionnaireResponse
- Local PROMIS T-score calculation via CQL
- Create Observation resources from $extract
- Transfer data to Site B via FHIR REST API

**Sample Questionnaire:**
- PROMIS Pain Interference 6a (LOINC panel: 62629-8)
- Response options from LOINC AnswerList LL358-3
- Ordinal values 1-5

### 3.2 Site B (Review Site) - HAPI FHIR

**Purpose:** Multi-site review and data display

**Configuration:**
- **Port:** 8082
- **Package:** `de.medizininformatikinitiative.kerndatensatz.pros:2026.0.0-rc.1`
- **PROMIS Version:** 2.0 (newer scoring algorithm - **DIFFERENT**)
- **Languages:** German (de-DE), English (en-US), Turkish (tr-TR pending)
- **Validation:** Enabled
- **Terminology Server:** http://terminology-proxy:3000/fhir

**Capabilities:**
- Receive QuestionnaireResponse from external sites
- Validate against PROMIS profiles
- Re-calculate scores using v2.0 algorithm
- Display in multiple languages
- Detect version mismatches

### 3.3 Terminology Service (Enhanced Proxy)

**Purpose:** Centralized terminology service with LOINC-specific enhancements

**Base Layer: ONTOSERVER**
- Standard FHIR terminology operations
- ValueSet/$expand
- CodeSystem/$lookup
- ConceptMap/$translate

**Enhancement Layer: FastAPI Wrapper**

New APIs needed (currently missing from standard terminology servers):

#### API 1: LOINC Panel Structure
```http
GET /loinc/Panel/{loincCode}?format=Questionnaire
```
**Purpose:** Convert LOINC panel code to FHIR Questionnaire structure

**Example:**
```http
GET /loinc/Panel/62629-8?format=Questionnaire

Response:
{
  "resourceType": "Questionnaire",
  "url": "http://loinc.org/Questionnaire/62629-8",
  "title": "PROMIS pain interference - version 1.0",
  "item": [
    {
      "linkId": "61758-9",
      "code": [{"system": "http://loinc.org", "code": "61758-9"}],
      "text": "How much did pain interfere with your day to day activities?",
      "type": "choice",
      "answerValueSet": "http://loinc.org/vs/LL358-3"
    }
  ]
}
```

**Status:** ❌ **Not available in LOINC FHIR service or ONTOSERVER**

#### API 2: Answer Lists with Ordinal Values
```http
GET /loinc/AnswerList/{answerListCode}?include=ordinals&version={version}
```
**Purpose:** Get LOINC answer list with ordinal scoring values

**Example:**
```http
GET /loinc/AnswerList/LL358-3?include=ordinals&version=1.0

Response:
{
  "resourceType": "ValueSet",
  "url": "http://loinc.org/vs/LL358-3",
  "version": "1.0",
  "expansion": {
    "contains": [
      {
        "code": "LA13863-8",
        "display": "Not at all",
        "designation": [
          {"language": "de", "value": "Überhaupt nicht"},
          {"language": "en", "value": "Not at all"},
          {"language": "tr", "value": "Hiç"}
        ],
        "extension": [{
          "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
          "valueDecimal": 1
        }]
      },
      {
        "code": "LA13909-9",
        "display": "A little bit",
        "designation": [
          {"language": "de", "value": "Ein wenig"},
          {"language": "en", "value": "A little bit"}
        ],
        "extension": [{
          "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
          "valueDecimal": 2
        }]
      }
      // ... more answers
    ]
  }
}
```

**Status:** ⚠️ **Partially available** (ordinals sometimes missing, version support unclear)

#### API 3: PROMIS Scoring Service
```http
POST /promis/$calculate-score
```
**Purpose:** Calculate PROMIS T-scores using IRT algorithms

**Example:**
```http
POST /promis/$calculate-score
Content-Type: application/json

{
  "scale": "pain-interference-6a",
  "version": "2.0",
  "responses": [
    {"item": "61758-9", "value": 4},
    {"item": "61769-6", "value": 3},
    {"item": "61773-8", "value": 4},
    {"item": "61777-9", "value": 3},
    {"item": "61781-1", "value": 2},
    {"item": "61785-2", "value": 3}
  ]
}

Response:
{
  "tScore": 58.3,
  "standardError": 3.1,
  "severity": "moderate",
  "algorithm": "IRT-EAP-v2.0",
  "interpretation": {
    "code": "moderate",
    "display": "Moderate pain interference",
    "range": "55-65 T-score"
  }
}
```

**Status:** ❌ **Not available** - Every system implements differently

#### API 4: Multi-Language ValueSet Expansion
```http
GET /ValueSet/$expand?url={valueSetUrl}&displayLanguage={lang1},{lang2}
```
**Purpose:** Expand ValueSet with multiple language designations in one call

**Status:** ⚠️ **Partially supported** - Need multiple calls for multiple languages

---

## 4. Data Flow Scenarios

### Scenario 1: Basic PROMIS Exchange ✅

**Flow:**
1. Site A: Patient completes PROMIS Pain questionnaire
2. Site A: Creates QuestionnaireResponse
3. Site A: Calculates T-score locally (CQL, v1.0 algorithm)
4. Site A: Creates Observation with score
5. Site A → Site B: Transfer Bundle (QuestionnaireResponse + Observation)
6. Site B: Receives and stores data
7. Site B: Displays in German UI

**APIs Used:**
- `POST /fhir/QuestionnaireResponse` (Site A)
- `GET /fhir/QuestionnaireResponse/{id}` (Site A)
- `POST /fhir/Bundle` (Site B)
- `GET /ValueSet/$expand` (Terminology Service)

**Result:** ✅ Works with standard FHIR

---

### Scenario 2: Version Mismatch Problem ⚠️

**Flow:**
1. Site A: Scores using v1.0 algorithm → T-score: 62.5
2. Site B: Receives response, validates against v2.0
3. Site B: Recalculates using v2.0 algorithm → T-score: 59.8
4. **PROBLEM:** Different scores for same raw responses!

**Technical Issues:**
- No standard way to declare scoring algorithm version in Observation
- No API to detect algorithm version mismatch
- No standard validation endpoint to check compatibility

**Missing API:**
```http
POST /Questionnaire/$validate-response
{
  "questionnaireResponse": {...},
  "targetVersion": "2.0",
  "checkScoring": true
}

Response:
{
  "valid": false,
  "issues": [
    {
      "severity": "warning",
      "code": "algorithm-mismatch",
      "details": "Response scored with v1.0, target system uses v2.0",
      "suggestion": "Recalculate score or document version in Observation.method"
    }
  ]
}
```

**Result:** ⚠️ Requires custom validation logic

---

### Scenario 3: Missing Translation ❌

**Flow:**
1. Site B: Turkish-speaking nurse needs to review response
2. Site B → Terminology Service: `GET /ValueSet/$expand?displayLanguage=tr`
3. Terminology Service: Returns codes without Turkish designations
4. Site B: Falls back to English or shows codes only

**Technical Issues:**
- No standard way to request "best available translation" with fallback chain
- No provenance for translation quality (official vs. community vs. machine)
- No mechanism to report missing translations

**Missing API:**
```http
GET /ValueSet/$expand?displayLanguage=tr-DE&fallback=de,en
X-Translation-Provenance: require

Response:
{
  "expansion": {
    "contains": [
      {
        "code": "LA13863-8",
        "display": "Not at all",
        "designation": [
          {
            "language": "de",
            "value": "Überhaupt nicht",
            "use": {"code": "fallback"}
          }
        ],
        "extension": [{
          "url": "translation-status",
          "valueCode": "missing-requested-language"
        }]
      }
    ]
  }
}
```

**Result:** ❌ Products must implement fallback logic themselves

---

### Scenario 4: Scoring Without Proprietary Libraries ❌

**Flow:**
1. Site B: Wants to recalculate PROMIS T-score
2. Site B: Has raw responses but no PROMIS IRT parameters
3. Options:
   - License PROMIS scoring software ($$$)
   - Implement IRT algorithm from papers (complex)
   - Use public R/Python packages (licensing unclear)
   - Call central scoring API (**doesn't exist**)

**Technical Issues:**
- No open-source validated PROMIS scoring libraries
- IRT parameters not in FHIR packages (copyright/licensing)
- Every site implements differently → incomparable results

**Needed Infrastructure:**
```http
POST /promis/$calculate-score
Authorization: Bearer {license-token}

# Central scoring service
# - Validated algorithms
# - Current IRT parameters
# - License management
# - Audit trail
```

**Result:** ❌ Major infrastructure gap

---

## 5. Product Feature Gaps

### 5.1 EHR Systems

| Feature | Current State | Impact | Priority |
|---------|---------------|--------|----------|
| FHIR Questionnaire rendering | ❌ Most use proprietary formats | Can't interoperate | High |
| Multi-language in forms | ❌ Limited or custom | Excludes non-German speakers | High |
| Terminology service integration | ⚠️ Some support, not standard | Manual code entry | Medium |
| Version warnings | ❌ Not implemented | Patient safety risk | High |
| PROMIS T-score display | ❌ Shows raw or custom calc | Incomparable across sites | Medium |

**Example Gap:**
```
Clinician at Site B views transferred PROMIS data:
- Sees: "Score: 62.5"
- Doesn't see: Algorithm version, calculation date, validity
- Risk: Misinterpretation if algorithms differ
```

### 5.2 Research EDC (REDCap, etc.)

| Feature | Current State | Impact | Priority |
|---------|---------------|--------|----------|
| FHIR export for PROMIS | ❌ Not standardized | Manual data transformation | High |
| Terminology server integration | ❌ Not available | Hard-coded value sets | Low |
| Standardized scoring | ❌ Custom calc fields | Incompatible implementations | High |
| Cross-site harmonization | ❌ Manual process | Research delays | Medium |

**Example Gap:**
```
Multi-center study using REDCap:
- 10 sites each configure PROMIS forms
- Each uses slightly different scoring logic
- Data pooling requires extensive cleaning
- No automated validation
```

### 5.3 FHIR Servers (HAPI, etc.)

| Feature | Current State | Impact | Priority |
|---------|---------------|--------|----------|
| PROMIS scoring via $extract | ⚠️ CQL possible but complex | Limited adoption | Medium |
| Version mismatch detection | ❌ Not implemented | Silent errors | High |
| Translation provenance | ❌ Not tracked | Can't audit translations | Low |
| LOINC panel → Questionnaire | ❌ Not available | Manual questionnaire creation | Medium |

**Example Gap:**
```
HAPI receives QuestionnaireResponse:
- Questionnaire version: 1.0
- Scoring algorithm: v1.0
- No automatic recalculation for v2.0
- No warning shown to users
```

### 5.4 Terminology Servers

| Feature | Current State | Impact | Priority |
|---------|---------------|--------|----------|
| LOINC panel structure API | ❌ Not available | Can't auto-generate questionnaires | High |
| Ordinal values in $expand | ⚠️ Incomplete | Manual ordinal lookup | High |
| PROMIS IRT scoring service | ❌ Not available | Fragmented implementations | High |
| Multi-version support | ⚠️ Limited | Can't compare across versions | Medium |
| Translation provenance | ❌ Not tracked | Unknown translation quality | Low |

---

## 6. Technical Pilot Opportunities

### 6.1 Infrastructure Pilots

#### Pilot A: Enhanced Terminology Proxy
**Objective:** Build wrapper around ONTOSERVER adding LOINC-specific APIs

**Scope:**
- LOINC Panel → Questionnaire conversion
- Answer lists with ordinal values
- Multi-language expansion (single call)
- Version-aware ValueSet expansion

**Tech Stack:**
- FastAPI (Python)
- ONTOSERVER (base)
- LOINC data files

**Effort:** 3-6 months, 1-2 developers

**Deliverable:** Open-source terminology proxy service

---

#### Pilot B: PROMIS Scoring Service
**Objective:** Centralized PROMIS T-score calculation API

**Scope:**
- IRT-based T-score calculation
- Support PROMIS v1.0 and v2.0 algorithms
- License management
- Audit trail

**Tech Stack:**
- Python/R with psychometric libraries
- PROMIS IRT parameters (license required)
- REST API

**Effort:** 6-12 months, 1 psychometrician + 1 developer

**Deliverable:** Production scoring service

**Challenges:**
- PROMIS licensing/costs
- Algorithm validation requirements
- Regulatory considerations (Medizinprodukt?)

---

#### Pilot C: Version Compatibility Service
**Objective:** Detect and warn about version mismatches

**Scope:**
- Questionnaire version registry
- Algorithm version mapping
- Compatibility checking API
- Migration recommendations

**Tech Stack:**
- Simple database (PostgreSQL)
- REST API
- FHIR StructureDefinition analysis

**Effort:** 3-6 months, 1 developer

**Deliverable:** Version compatibility checker

---

### 6.2 Product Feature Pilots

#### Pilot D: FHIR Questionnaire Renderer
**Objective:** Multi-language web component for FHIR Questionnaires

**Scope:**
- React/Vue component
- FHIR Questionnaire R4 support
- Real-time terminology lookups
- Language switching
- SMART app integration

**Tech Stack:**
- React/TypeScript
- FHIR client libraries
- SMART on FHIR

**Effort:** 3-6 months, 1-2 frontend developers

**Deliverable:** Open-source component library

---

#### Pilot E: REDCap FHIR Bridge
**Objective:** Standardized PROMIS export from REDCap to FHIR

**Scope:**
- REDCap External Module
- Map REDCap forms to FHIR Questionnaire
- Export responses as QuestionnaireResponse
- Include scoring as Observation

**Tech Stack:**
- PHP (REDCap platform)
- FHIR PHP libraries

**Effort:** 2-4 months, 1 REDCap developer

**Deliverable:** REDCap External Module

---

#### Pilot F: HAPI Version Detection Plugin
**Objective:** Add version mismatch warnings to HAPI FHIR

**Scope:**
- Interceptor for QuestionnaireResponse
- Check questionnaire version vs. server packages
- Warning in OperationOutcome if mismatch
- Suggestion for resolution

**Tech Stack:**
- Java (HAPI platform)
- HAPI Interceptor API

**Effort:** 1-3 months, 1 Java developer

**Deliverable:** HAPI FHIR plugin

---

## 7. Standards Gaps & Recommendations

### 7.1 FHIR Specification Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No standard extension for scoring algorithm version | Can't track which algorithm was used | Propose `Observation.method` CodeSystem |
| No QuestionnaireResponse version validation operation | Silent compatibility issues | Propose `$validate-response` operation |
| Limited translation provenance | Unknown translation quality | Enhance `designation.use` binding |
| No LOINC panel operations | Manual Questionnaire creation | Propose LOINC-specific operations |

### 7.2 LOINC FHIR Service Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No panel structure API | Can't auto-generate questionnaires | Work with Regenstrief to add endpoint |
| Incomplete ordinal values | Manual scoring logic | Request ordinal values in all AnswerLists |
| No multi-version support | Can't compare historical data | Request version parameter support |

### 7.3 Terminology Service Gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| No PROMIS scoring APIs | Fragmented implementations | Community-developed scoring service |
| Limited multi-language support | Multiple API calls needed | Enhance $expand for multi-lang in one call |
| No translation workflow | Ad-hoc translation process | Standardize translation submission/approval |

---

## 8. Implementation Roadmap

### Phase 1: Core Infrastructure (Months 1-6)
- ✅ Deploy enhanced terminology proxy
- ✅ Implement LOINC panel API
- ✅ Add ordinal value support
- ✅ Multi-language expansion

### Phase 2: Product Features (Months 3-9)
- ✅ FHIR Questionnaire renderer component
- ✅ REDCap FHIR export
- ✅ HAPI version detection plugin

### Phase 3: Advanced Services (Months 6-18)
- ✅ PROMIS scoring service (pending licensing)
- ✅ Version compatibility checker
- ✅ Translation management workflow

### Phase 4: Governance & Operations (Ongoing)
- ✅ Establish terminology service governance
- ✅ Define translation validation process
- ✅ Create sustainability model

---

## 9. Cost Estimates

### Infrastructure Costs (Annual)

| Component | Cost | Notes |
|-----------|------|-------|
| Server hosting | €10-20k | Terminology service, APIs |
| ONTOSERVER license | €5-15k | Depending on usage tier |
| LOINC license | €0 | Free for healthcare use |
| PROMIS scoring license | €10-50k | Varies by usage volume |
| Operations/DevOps | €50-100k | Maintenance, support |
| **Total** | **€75-185k** | |

### Development Costs (One-time)

| Pilot | Effort | Cost Estimate |
|-------|--------|---------------|
| Enhanced terminology proxy | 6 person-months | €60-90k |
| PROMIS scoring service | 12 person-months | €120-180k |
| Version compatibility service | 4 person-months | €40-60k |
| FHIR Questionnaire renderer | 6 person-months | €60-90k |
| REDCap FHIR bridge | 3 person-months | €30-45k |
| HAPI version plugin | 2 person-months | €20-30k |
| **Total** | **33 person-months** | **€330-495k** |

---

## 10. Getting Started

### For Participants Who Want to Test

**Option 1: Run Demo Locally**
```bash
# Clone repository
git clone <repo-url>
cd fhir-sdc-questionnaire-service

# Start demo environment
docker compose -f docker-compose.workshop.yml up

# Access components
# - Site A: http://localhost:8081/fhir
# - Site B: http://localhost:8082/fhir
# - Terminology: http://localhost:3000/fhir
# - Demo UI: http://localhost:8000
```

**Option 2: Deploy to Your Infrastructure**
- Adapt docker-compose for your environment
- Point to your existing terminology server
- Load your PROMIS packages
- Test with your use cases

**Option 3: Build Specific Pilot**
- Choose pilot from section 6
- Coordinate with other participants
- Access reference implementations
- Contribute back to community

### Support & Coordination

- **Technical Documentation:** See `/docs` folder
- **API Specifications:** OpenAPI specs in `/api-specs`
- **Code Examples:** See `/examples` folder
- **Issue Tracking:** GitHub Issues
- **Discussion Forum:** [TBD - MII workspace? HL7 Zulip?]

---

## 11. Discussion Questions for Workshop

### Technical Architecture
1. Is the terminology proxy architecture sufficient?
2. Should scoring be centralized or distributed?
3. How to handle terminology server outages?
4. What authentication/authorization model for APIs?

### Product Priorities
1. Which product gaps are most urgent?
2. EHR integration vs. research tools - which first?
3. Commercial products vs. open source?
4. Who should build what?

### Standards & Interoperability
1. Should we propose FHIR extensions for scoring metadata?
2. Work with Regenstrief on LOINC API enhancements?
3. Engage PROMIS Health Organization on licensing?
4. Create German/European PROMIS consortium?

### Sustainability
1. Who operates the national terminology service?
2. Funding model: MII core budget? User fees? Grants?
3. Governance: Who decides priorities?
4. How to ensure long-term maintenance?

---

## 12. Next Steps After Workshop

1. **Immediate (Week 1-2)**
   - Survey participants for pilot interest
   - Form working groups by pilot area
   - Schedule technical deep-dive sessions

2. **Short-term (Months 1-3)**
   - Launch 2-3 initial pilots
   - Establish technical coordination
   - Set up shared infrastructure

3. **Medium-term (Months 3-12)**
   - Deliver pilot MVPs
   - Test in real-world scenarios
   - Iterate based on feedback

4. **Long-term (Year 2+)**
   - Production deployment
   - Governance structure
   - Sustainability planning

---

## Appendix A: Glossary

- **PROMIS:** Patient-Reported Outcomes Measurement Information System
- **IRT:** Item Response Theory (psychometric scoring method)
- **T-score:** Standardized score (mean=50, SD=10)
- **LOINC:** Logical Observation Identifiers Names and Codes
- **MII PRO:** Medizininformatik Initiative Patient-Reported Outcomes
- **SDC:** Structured Data Capture (FHIR IG)
- **CQL:** Clinical Quality Language (scoring logic)

---

## Appendix B: References

- [FHIR Questionnaire Resource](http://hl7.org/fhir/questionnaire.html)
- [FHIR SDC Implementation Guide](http://hl7.org/fhir/uv/sdc/)
- [PROMIS Health Organization](https://www.healthmeasures.net/explore-measurement-systems/promis)
- [LOINC FHIR API](https://fhir.loinc.org/)
- [MII PRO Implementation Guide](https://simplifier.net/guide/MedizininformatikInitiative-ModulPRO)

---

**Document Version:** 1.0
**Last Updated:** 2024-11-27
**Contact:** [Workshop Organizer Contact Info]
