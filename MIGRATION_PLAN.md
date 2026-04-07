# Repository Split Migration Plan

This document describes the plan to split `fhir-sdc-questionnaire-service` into two separate repositories.

## Target Repositories

### 1. `fhir-sdc-api` - Core SDC Implementation
The main SDC API service with FHIR server testing infrastructure.

### 2. `fhir-workshop-demo` - Workshop Materials
Multi-site demonstration environment for PROMIS exchange scenarios.

---

## File Distribution

### Repository: `fhir-sdc-api`

```
fhir-sdc-api/
├── api/                              # FastAPI service
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── routers/
│   │   └── services/
│   ├── tests/
│   │   ├── README.md
│   │   ├── conftest.py
│   │   ├── integration/
│   │   └── sdc_compliance/
│   ├── Dockerfile
│   ├── pytest.ini
│   ├── requirements.txt
│   └── requirements-test.txt
├── hapi-config/                      # HAPI FHIR configuration
│   └── application.yaml
├── hapi-scripts/                     # HAPI setup scripts
│   └── *.sh
├── scripts/                          # Utility scripts
│   ├── install-isik-runtime.py
│   ├── install-isik.sh
│   ├── install_mii_package.py
│   ├── backup.sh
│   ├── restore.sh
│   └── check-server-versions.sh
├── .github/
│   └── workflows/
│       └── test.yml                  # CI/CD pipeline
├── docker-compose.yml                # Main development environment
├── docker-compose.test.yml           # Test environment (H2 in-memory)
├── docker-compose.aidbox.yml         # Aidbox alternative
├── .env.example
├── .gitignore
├── README.md                         # NEW: API-focused readme
│
# Documentation (API-focused)
├── ARCHITECTURE.md
├── REQUIREMENTS.md
├── SDC_FORM_MANAGER_REQUIREMENTS.md
├── FORM_MANAGER_CAPABILITIES.md
├── TEST_REQUIREMENTS_MAPPING.md
├── TESTING.md
├── TESTING_ACCOMPLISHMENTS.md
├── MULTI_SERVER_TESTING.md
├── SDC_CONFIGURATION.md
├── FHIR_VALIDATOR_INTEGRATION.md
├── FHIR_SERVER_VERSIONS.md
├── VERSION_QUICK_REFERENCE.md
├── VERSION_IN_METADATA_EXPLAINED.md
├── IMPLEMENTING_ASSEMBLE_OPERATION.md
├── ASSEMBLE_OPERATION_SUMMARY.md
├── PRODUCTION_STATUS.md
├── KNOWN_LIMITATIONS.md
└── REFERENCE_IMPLEMENTATION_PLAN.md
```

### Repository: `fhir-workshop-demo`

```
fhir-workshop-demo/
├── demo-ui/                          # Workshop UI
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── terminology-proxy/                # LOINC wrapper service
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── workshop-config/                  # Site A/B HAPI configs
│   ├── site-a-application.yaml
│   └── site-b-application.yaml
├── workshop-scripts/                 # Package installers
│   ├── install_packages.py
│   └── load_sample_data.py
├── workshop-scenarios/               # Demo scenarios
│   └── PHQ9_DEMO.md
├── docker-compose.yml                # Main orchestration (was docker-compose.workshop.yml)
├── .env.example
├── .gitignore
├── README.md                         # NEW: Workshop-focused readme (was WORKSHOP_README.md)
└── ARCHITECTURE.md                   # Workshop architecture (was WORKSHOP_ARCHITECTURE.md)
```

---

## Files NOT Migrated (Delete or Archive)

These files are specific to the combined repo structure:

| File | Reason |
|------|--------|
| `CLAUDE.md` | Describes combined structure; each repo gets its own |
| `docs/` | Generated HTML; regenerate per repo if needed |
| `*.pptx`, `*.pdf` | Presentation files; store separately or in workshop repo |

---

## Changes Required

### 1. Port Conflict Resolution

**Current conflict:** Both main API and demo-ui use port 8000.

**Fix in `fhir-workshop-demo`:**
- Change demo-ui from port `8000` to `8100`
- Update docker-compose.yml and all documentation

### 2. Version Pinning

**Current issue:** Docker images use `latest` tag.

**Fix in both repos:**
```yaml
# Pin HAPI version
image: hapiproject/hapi:v8.4.0

# Pin PostgreSQL version
image: postgres:15-alpine

# Pin Ontoserver version (workshop only)
image: aehrc/ontoserver:6.14.0
```

### 3. Dependency Standardization (Optional)

**Current mismatch:**
- API: FastAPI 0.109.0
- Workshop: FastAPI 0.104.1

**Recommendation:** Update workshop to 0.109.0 for consistency, or leave as-is since they're independent.

---

## Migration Commands

### Step 1: Create New Repositories

```bash
# Create fhir-sdc-api
cd /Users/thome/code/interop-prototypes
mkdir fhir-sdc-api
cd fhir-sdc-api
git init

# Create fhir-workshop-demo
cd /Users/thome/code/interop-prototypes
mkdir fhir-workshop-demo
cd fhir-workshop-demo
git init
```

### Step 2: Copy Files to fhir-sdc-api

```bash
cd /Users/thome/code/interop-prototypes/fhir-sdc-questionnaire-service

# Core directories
cp -r api ../fhir-sdc-api/
cp -r hapi-config ../fhir-sdc-api/
cp -r hapi-scripts ../fhir-sdc-api/
cp -r scripts ../fhir-sdc-api/
cp -r .github ../fhir-sdc-api/

# Docker files
cp docker-compose.yml ../fhir-sdc-api/
cp docker-compose.test.yml ../fhir-sdc-api/
cp docker-compose.aidbox.yml ../fhir-sdc-api/
cp .env ../fhir-sdc-api/.env.example
cp .gitignore ../fhir-sdc-api/

# Documentation
cp ARCHITECTURE.md ../fhir-sdc-api/
cp REQUIREMENTS.md ../fhir-sdc-api/
cp SDC_FORM_MANAGER_REQUIREMENTS.md ../fhir-sdc-api/
cp FORM_MANAGER_CAPABILITIES.md ../fhir-sdc-api/
cp TEST_REQUIREMENTS_MAPPING.md ../fhir-sdc-api/
cp TESTING.md ../fhir-sdc-api/
cp TESTING_ACCOMPLISHMENTS.md ../fhir-sdc-api/
cp MULTI_SERVER_TESTING.md ../fhir-sdc-api/
cp SDC_CONFIGURATION.md ../fhir-sdc-api/
cp FHIR_VALIDATOR_INTEGRATION.md ../fhir-sdc-api/
cp FHIR_SERVER_VERSIONS.md ../fhir-sdc-api/
cp VERSION_QUICK_REFERENCE.md ../fhir-sdc-api/
cp VERSION_IN_METADATA_EXPLAINED.md ../fhir-sdc-api/
cp IMPLEMENTING_ASSEMBLE_OPERATION.md ../fhir-sdc-api/
cp ASSEMBLE_OPERATION_SUMMARY.md ../fhir-sdc-api/
cp PRODUCTION_STATUS.md ../fhir-sdc-api/
cp KNOWN_LIMITATIONS.md ../fhir-sdc-api/
cp REFERENCE_IMPLEMENTATION_PLAN.md ../fhir-sdc-api/
```

### Step 3: Copy Files to fhir-workshop-demo

```bash
cd /Users/thome/code/interop-prototypes/fhir-sdc-questionnaire-service

# Core directories
cp -r demo-ui ../fhir-workshop-demo/
cp -r terminology-proxy ../fhir-workshop-demo/
cp -r workshop-config ../fhir-workshop-demo/
cp -r workshop-scripts ../fhir-workshop-demo/
cp -r workshop-scenarios ../fhir-workshop-demo/

# Docker file (renamed)
cp docker-compose.workshop.yml ../fhir-workshop-demo/docker-compose.yml

# Documentation (renamed)
cp WORKSHOP_README.md ../fhir-workshop-demo/README.md
cp WORKSHOP_ARCHITECTURE.md ../fhir-workshop-demo/ARCHITECTURE.md

# Git config
cp .gitignore ../fhir-workshop-demo/
```

### Step 4: Apply Fixes

See the automated migration script below.

---

## Migration Script

A shell script `migrate-repos.sh` will be created to automate this process.

Run it from the parent directory:
```bash
cd /Users/thome/code/interop-prototypes
./fhir-sdc-questionnaire-service/migrate-repos.sh
```

---

## Post-Migration Checklist

### For `fhir-sdc-api`:
- [ ] Update README.md with new repo structure
- [ ] Test `docker compose up -d`
- [ ] Run `cd api && pytest tests/ -v`
- [ ] Verify CI/CD pipeline works
- [ ] Update any hardcoded repo URLs in docs

### For `fhir-workshop-demo`:
- [ ] Verify port 8100 works for demo-ui
- [ ] Test `docker compose up -d`
- [ ] Update README.md with new URLs
- [ ] Verify all services start correctly
- [ ] Add basic health check tests

### For original repo:
- [ ] Archive or delete after migration verified
- [ ] Update any external references pointing here

---

## Rollback Plan

If migration fails:
1. Both new repos can be deleted
2. Original repo remains unchanged
3. No data loss possible (copy, not move)
