# Workshop Setup Guide

## Quick Start

```bash
# Clone repository
git clone <repo-url>
cd fhir-sdc-questionnaire-service

# Start workshop environment
docker compose -f docker-compose.workshop.yml up -d

# Wait 2-3 minutes for services to initialize
# Watch logs:
docker compose -f docker-compose.workshop.yml logs -f

# Access Demo UI
open http://localhost:8000
```

## Architecture Overview

The workshop environment consists of:

1. **Site A (Port 8081)** - German hospital, data collection, PROMIS v1.0 + PHQ-9
2. **Site B (Port 8082)** - Multi-site clinic, data review, PROMIS v2.0 + PHQ-9
3. **Terminology Proxy (Port 3000)** - Enhanced LOINC terminology service (PROMIS + PHQ-9)
4. **Demo UI (Port 8000)** - Interactive scenario controller

**Sample Questionnaires Available:**
- PROMIS Pain Interference 6a (LOINC: 62629-8)
- PHQ-9 Depression Screening (LOINC: 44249-1)

## Services

| Service | URL | Description |
|---------|-----|-------------|
| Demo UI | http://localhost:8000 | Interactive workshop scenarios |
| Site A FHIR | http://localhost:8081/fhir | Collection site HAPI server |
| Site B FHIR | http://localhost:8082/fhir | Review site HAPI server |
| Terminology | http://localhost:3000 | Enhanced terminology proxy |
| Site A Swagger | http://localhost:8081/fhir/swagger-ui/ | HAPI REST API docs |
| Site B Swagger | http://localhost:8082/fhir/swagger-ui/ | HAPI REST API docs |
| Demo API Docs | http://localhost:8000/docs | FastAPI Swagger docs |

## SMART on FHIR Integration

### Option 1: Use LHC-Forms (Recommended)

LHC-Forms is NLM's FHIR Questionnaire renderer with SMART integration.

**Quick test with LHC-Forms:**

```html
<!-- Save as smart-app.html -->
<!DOCTYPE html>
<html>
<head>
    <title>PROMIS SMART App</title>
    <script src="https://cdn.jsdelivr.net/npm/fhirclient/build/fhir-client.js"></script>
    <script src="https://clinicaltables.nlm.nih.gov/lforms-versions/30.0.2/webcomponent/assets/lib/zone.min.js"></script>
    <script src="https://clinicaltables.nlm.nih.gov/lforms-versions/30.0.2/webcomponent/lhc-forms.js"></script>
</head>
<body>
    <h1>PROMIS Pain Interference</h1>
    <lhc-form></lhc-form>

    <script>
        // SMART on FHIR launch
        FHIR.oauth2.ready().then(client => {
            // Load PROMIS questionnaire
            client.request("Questionnaire/promis-pain-interference-6a-demo")
                .then(q => {
                    // Render with LHC-Forms
                    document.querySelector('lhc-form').setFHIRContext({
                        client: client
                    });
                    LForms.Util.addFormToPage(q, 'lhc-form');
                });
        }).catch(console.error);
    </script>
</body>
</html>
```

### Option 2: SMART Launcher for Testing

```bash
# Use SMART Health IT launcher
# 1. Go to: https://launch.smarthealthit.org/
# 2. Configure:
#    - FHIR Server: http://localhost:8081/fhir
#    - App Launch URL: http://localhost:8080/smart-app.html
# 3. Launch app
```

### Option 3: Simple Static Demo (No SMART)

For workshop without SMART complexity, use the demo UI at http://localhost:8000

## Demo Scenarios

### Scenario 1: Basic PROMIS Exchange ✅

**Demonstrates:** Working FHIR exchange

```bash
# Via Demo UI
open http://localhost:8000
# Click "Run Scenario" for "Basic PROMIS Exchange"

# Or via API
curl http://localhost:8000/api/scenarios/basic
```

**What it shows:**
- Questionnaire retrieval from Site A
- ValueSet expansion from terminology service
- Standard FHIR operations work correctly

### Scenario 2: Version Mismatch ⚠️

**Demonstrates:** Scoring algorithm version conflict

```bash
# Via Demo UI or:
curl http://localhost:8000/api/scenarios/version-mismatch
```

**What it shows:**
- Site A uses PROMIS v1.0 scoring (ordinals 1-5)
- Site B uses PROMIS v2.0 scoring (ordinals 5-1, **REVERSED!**)
- Same response = different scores = patient safety risk

**Key Learning:** Need version-aware validation APIs

### Scenario 3: Missing Translation ❌

**Demonstrates:** Incomplete multilingual support

```bash
# Via Demo UI or:
curl http://localhost:8000/api/scenarios/missing-translation
```

**What it shows:**
- German translation: Complete ✅
- Turkish translation: Partially missing ❌
- No standard fallback mechanism

**Key Learning:** Products must implement fallback logic

### Scenario 4: LOINC Panel API ⚠️

**Demonstrates:** Missing LOINC panel structure API

```bash
# Via Demo UI or:
curl http://localhost:8000/api/scenarios/loinc-panel

# Try enhanced API directly:
curl http://localhost:3000/loinc/Panel/62629-8?format=Questionnaire
```

**What it shows:**
- Standard LOINC FHIR service: No panel structure API ❌
- Enhanced wrapper: Converts LOINC panel to Questionnaire ✅

**Key Learning:** Need standardized LOINC enhancement APIs

## Manual Testing

### Test Terminology API

```bash
# PROMIS Pain Interference answer list with ordinals (v1.0)
curl "http://localhost:3000/loinc/AnswerList/LL358-3?version=1.0" | jq

# Get with v2.0 (reversed ordinals!)
curl "http://localhost:3000/loinc/AnswerList/LL358-3?version=2.0" | jq

# Get German translation
curl "http://localhost:3000/loinc/AnswerList/LL358-3?displayLanguage=de" | jq

# Get Turkish (partially missing)
curl "http://localhost:3000/loinc/AnswerList/LL358-3?displayLanguage=tr" | jq

# Get PROMIS panel as Questionnaire
curl "http://localhost:3000/loinc/Panel/62629-8?format=Questionnaire" | jq

# PHQ-9 answer list with ordinals
curl "http://localhost:3000/loinc/AnswerList/LL358-9?include=ordinals" | jq

# PHQ-9 panel as Questionnaire
curl "http://localhost:3000/loinc/Panel/44249-1?format=Questionnaire" | jq

# PHQ-9 in German
curl "http://localhost:3000/loinc/AnswerList/LL358-9?displayLanguage=de" | jq
```

### Test FHIR Servers

```bash
# Site A metadata
curl http://localhost:8081/fhir/metadata | jq .fhirVersion

# Site B metadata
curl http://localhost:8082/fhir/metadata | jq .fhirVersion

# Search Questionnaires on Site A
curl "http://localhost:8081/fhir/Questionnaire?_summary=true" | jq

# Get specific questionnaires
curl "http://localhost:8081/fhir/Questionnaire/promis-pain-interference-6a-demo" | jq
curl "http://localhost:8081/fhir/Questionnaire/phq-9-demo" | jq

# Search QuestionnaireResponses
curl "http://localhost:8081/fhir/QuestionnaireResponse?_summary=true" | jq

# Get specific responses
curl "http://localhost:8081/fhir/QuestionnaireResponse/demo-response-1" | jq  # PROMIS
curl "http://localhost:8081/fhir/QuestionnaireResponse/demo-response-phq9-1" | jq  # PHQ-9
```

### Create Test QuestionnaireResponse

```bash
curl -X POST http://localhost:8081/fhir/QuestionnaireResponse \
  -H "Content-Type: application/fhir+json" \
  -d '{
    "resourceType": "QuestionnaireResponse",
    "questionnaire": "http://loinc.org/Questionnaire/62629-8",
    "status": "completed",
    "authored": "2024-11-27T12:00:00Z",
    "item": [{
      "linkId": "61758-9",
      "answer": [{
        "valueCoding": {
          "system": "http://loinc.org",
          "code": "LA13914-9",
          "display": "Quite a bit"
        }
      }]
    }]
  }'
```

### Transfer Response to Site B

```bash
# Get from Site A
RESPONSE=$(curl -s http://localhost:8081/fhir/QuestionnaireResponse/demo-response-1)

# Post to Site B
echo $RESPONSE | curl -X POST http://localhost:8082/fhir/QuestionnaireResponse \
  -H "Content-Type: application/fhir+json" \
  -d @-
```

## Troubleshooting

### Services not starting

```bash
# Check status
docker compose -f docker-compose.workshop.yml ps

# View logs
docker compose -f docker-compose.workshop.yml logs

# Restart specific service
docker compose -f docker-compose.workshop.yml restart hapi-site-a
```

### HAPI taking long to start

HAPI FHIR can take 2-3 minutes to:
1. Initialize database schema
2. Download and install packages
3. Index resources

**Wait for log message:** `Started Application in X seconds`

### Terminology proxy errors

```bash
# Check terminology proxy logs
docker compose -f docker-compose.workshop.yml logs terminology-proxy

# Check if ONTOSERVER is running (optional component)
docker compose -f docker-compose.workshop.yml logs ontoserver

# Test directly
curl http://localhost:3000/health
```

### Package installation issues

MII PRO packages are installed from Simplifier. If download fails:

```bash
# Check package installer logs
docker compose -f docker-compose.workshop.yml logs package-installer

# Manually trigger (if container exited)
docker compose -f docker-compose.workshop.yml run package-installer
```

### Port conflicts

If ports 8080, 8081, 8082, 3000, or 8000 are in use:

Edit `docker-compose.workshop.yml` and change port mappings:

```yaml
ports:
  - "8091:8080"  # Change 8081 to 8091
```

### Reset everything

```bash
# Stop and remove all containers, volumes
docker compose -f docker-compose.workshop.yml down -v

# Start fresh
docker compose -f docker-compose.workshop.yml up -d
```

## Workshop Discussion Points

### Technical Challenges Demonstrated

1. **Version Management**
   - How to detect version mismatches?
   - How to validate compatibility?
   - Should old responses be recalculated with new algorithms?

2. **Terminology Services**
   - What APIs are missing from standards?
   - LOINC panel structure not in FHIR API
   - Ordinal values not consistently included
   - Multi-language fallback not standardized

3. **Product Gaps**
   - EHR systems don't render FHIR Questionnaires
   - No standard translation handling
   - Scoring implementations vary across sites
   - No version warning mechanisms

4. **Standards Gaps**
   - No standard extension for scoring algorithm version
   - No $validate-response operation for compatibility
   - Limited translation provenance
   - No LOINC-specific operations

### Pilot Opportunities

1. **Enhanced Terminology Proxy** (3-6 months)
   - LOINC panel APIs
   - Ordinal values support
   - Multi-language enhancements

2. **PROMIS Scoring Service** (6-12 months)
   - Centralized IRT calculations
   - License management
   - Audit trail

3. **Version Compatibility Checker** (3-6 months)
   - Detect mismatches
   - Recommend migrations
   - Track algorithm versions

4. **Product Integrations**
   - FHIR Questionnaire renderer (3-6 months)
   - REDCap FHIR export (2-4 months)
   - HAPI version detection plugin (1-3 months)

## Next Steps

1. **Run all demo scenarios** to understand technical challenges
2. **Review WORKSHOP_ARCHITECTURE.md** for detailed technical specs
3. **Discuss priorities** for pilot projects
4. **Identify partners** for collaboration
5. **Plan pilot projects** with realistic timelines and resources

## Support

- **Technical Documentation:** See WORKSHOP_ARCHITECTURE.md
- **API Documentation:** http://localhost:8000/docs (when running)
- **Issues:** GitHub Issues (TBD)
- **Coordination:** [Workshop organizer contact]

## License

Workshop demo materials: [TBD]
MII PRO packages: See individual package licenses
HAPI FHIR: Apache 2.0
LHC-Forms: MIT
