# FHIR Workshop Demo

Multi-site demonstration environment for PROMIS questionnaire exchange, showcasing interoperability challenges and solutions.

## What This Demonstrates

This workshop environment simulates two hospital sites exchanging PROMIS and PHQ-9 questionnaires, highlighting real-world interoperability challenges:

1. **Version Mismatch** - Different scoring algorithm versions between sites
2. **Missing Translations** - Incomplete multilingual support
3. **LOINC Panel Gaps** - Standard APIs missing panel structure information
4. **Cross-Site Exchange** - Transferring questionnaire responses between systems

## Quick Start

```bash
# Clone repository
git clone <repo-url>
cd fhir-workshop-demo

# Start workshop environment
docker compose up -d

# Wait 2-3 minutes for services to initialize
docker compose logs -f

# Access Demo UI
open http://localhost:8100
```

## Architecture

```
                         ┌──────────────────┐
                         │    Demo UI       │ :8100
                         │ Scenario Control │
                         └────────┬─────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
┌─────────▼─────────┐   ┌────────▼────────┐   ┌─────────▼─────────┐
│    Site A HAPI    │   │    Site B HAPI  │   │ Terminology Proxy │
│  (Collection)     │   │    (Review)     │   │    (LOINC)        │
│  PROMIS v1.0      │   │   PROMIS v2.0   │   │                   │
│      :8081        │   │      :8082      │   │      :3000        │
└─────────┬─────────┘   └────────┬────────┘   └─────────┬─────────┘
          │                      │                      │
┌─────────▼─────────┐   ┌────────▼────────┐   ┌────────▼─────────┐
│   PostgreSQL A    │   │  PostgreSQL B   │   │   ONTOSERVER     │
└───────────────────┘   └─────────────────┘   └──────────────────┘
```

## Services

| Service | Port | URL | Description |
|---------|------|-----|-------------|
| Demo UI | 8100 | http://localhost:8100 | Interactive scenarios |
| Site A FHIR | 8081 | http://localhost:8081/fhir | Collection site |
| Site B FHIR | 8082 | http://localhost:8082/fhir | Review site |
| Terminology Proxy | 3000 | http://localhost:3000 | Enhanced LOINC API |
| Demo API Docs | 8100 | http://localhost:8100/docs | FastAPI Swagger |

## Demo Scenarios

### Scenario 1: Basic PROMIS Exchange
**Demonstrates:** Working FHIR exchange

Shows standard questionnaire retrieval and ValueSet expansion working correctly.

### Scenario 2: Version Mismatch
**Demonstrates:** Scoring algorithm version conflict

- Site A uses PROMIS v1.0 scoring (ordinals 1-5)
- Site B uses PROMIS v2.0 scoring (ordinals 5-1, **REVERSED**)
- Same response = different scores = patient safety risk

### Scenario 3: Missing Translation
**Demonstrates:** Incomplete multilingual support

- German translation: Complete
- Turkish translation: Partially missing
- No standard fallback mechanism

### Scenario 4: LOINC Panel API
**Demonstrates:** Missing LOINC panel structure API

Shows how the terminology proxy provides LOINC panel-to-Questionnaire conversion that standard FHIR terminology servers don't offer.

## Manual Testing

### Test Terminology API

```bash
# PROMIS answer list with ordinals (v1.0)
curl "http://localhost:3000/loinc/AnswerList/LL358-3?version=1.0" | jq

# Same with v2.0 (reversed ordinals!)
curl "http://localhost:3000/loinc/AnswerList/LL358-3?version=2.0" | jq

# German translation
curl "http://localhost:3000/loinc/AnswerList/LL358-3?displayLanguage=de" | jq

# PROMIS panel as Questionnaire
curl "http://localhost:3000/loinc/Panel/62629-8?format=Questionnaire" | jq

# PHQ-9 panel as Questionnaire
curl "http://localhost:3000/loinc/Panel/44249-1?format=Questionnaire" | jq
```

### Test FHIR Servers

```bash
# Site A metadata
curl http://localhost:8081/fhir/metadata | jq .fhirVersion

# Site B metadata
curl http://localhost:8082/fhir/metadata | jq .fhirVersion

# Search Questionnaires on Site A
curl "http://localhost:8081/fhir/Questionnaire?_summary=true" | jq

# Get PROMIS questionnaire
curl "http://localhost:8081/fhir/Questionnaire/promis-pain-interference-6a-demo" | jq

# Get PHQ-9 questionnaire
curl "http://localhost:8081/fhir/Questionnaire/phq-9-demo" | jq
```

### Transfer Response Between Sites

```bash
# Get from Site A
RESPONSE=$(curl -s http://localhost:8081/fhir/QuestionnaireResponse/demo-response-1)

# Post to Site B
echo $RESPONSE | curl -X POST http://localhost:8082/fhir/QuestionnaireResponse \
  -H "Content-Type: application/fhir+json" \
  -d @-
```

## Sample Questionnaires

| Questionnaire | LOINC Code | Description |
|---------------|------------|-------------|
| PROMIS Pain Interference 6a | 62629-8 | Pain interference assessment |
| PHQ-9 | 44249-1 | Depression screening |

## Project Structure

```
fhir-workshop-demo/
├── demo-ui/                # Workshop UI (FastAPI + HTML)
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── terminology-proxy/      # LOINC wrapper service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── workshop-config/        # HAPI configurations
│   ├── site-a-application.yaml
│   └── site-b-application.yaml
├── workshop-scripts/       # Setup scripts
│   ├── install_packages.py
│   └── load_sample_data.py
├── workshop-scenarios/     # Scenario descriptions
│   └── PHQ9_DEMO.md
├── docker-compose.yml      # Main orchestration
└── ARCHITECTURE.md         # Technical details
```

## Troubleshooting

### Services not starting

```bash
# Check status
docker compose ps

# View logs
docker compose logs

# HAPI takes 2-3 minutes to initialize
docker compose logs -f hapi-site-a
```

### Port conflicts

If ports 8081, 8082, 3000, or 8100 are in use, edit `docker-compose.yml`:

```yaml
ports:
  - "8091:8080"  # Change external port
```

### Reset everything

```bash
docker compose down -v
docker compose up -d
```

## Workshop Discussion Points

### Technical Challenges

1. **Version Management** - How to detect and handle version mismatches?
2. **Terminology Services** - What APIs are missing from standards?
3. **Product Gaps** - EHR systems don't render FHIR Questionnaires
4. **Standards Gaps** - No standard scoring algorithm version extension

### Pilot Opportunities

1. Enhanced Terminology Proxy (LOINC panels, ordinals, multi-language)
2. PROMIS Scoring Service (centralized IRT calculations)
3. Version Compatibility Checker
4. FHIR Questionnaire renderer for EHR integration

## License

Workshop demo materials: [TBD]
MII PRO packages: See individual package licenses
HAPI FHIR: Apache 2.0

## Related Projects

- [fhir-sdc-api](https://github.com/your-org/fhir-sdc-api) - SDC API implementation
