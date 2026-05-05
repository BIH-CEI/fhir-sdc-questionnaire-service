# Project Overview

This repository contains components for FHIR SDC (Structured Data Capture) questionnaire handling: a reference implementation API on top of HAPI FHIR, plus planning documentation.

---

## Components

### 1. SDC API Service (`api/`)
FastAPI service providing SDC operations on top of HAPI FHIR.

| Path | Description |
|------|-------------|
| `api/app/main.py` | FastAPI entry point |
| `api/app/routers/` | Routes for `$package`, `$localize`, etc. |
| `api/app/services/` | Business logic (PackageService, LocalizationService) |
| `api/tests/` | Pytest test suite (21+ SDC compliance tests) |
| `api/Dockerfile` | Container build |

### 2. Main Docker Setup
| File | Description |
|------|-------------|
| `docker-compose.yml` | Main dev environment (single HAPI + API) |
| `docker-compose.test.yml` | Test environment |
| `docker-compose.aidbox.yml` | Alternative using Aidbox instead of HAPI |
| `hapi-config/` | HAPI configuration |
| `hapi-scripts/` | IG installation scripts |

### 3. Utility Scripts (`scripts/`)
| Script | Description |
|--------|-------------|
| `install_mii_package.py` | Install MII PRO IG |
| `install-isik.sh` | Install ISiK (German interop) |
| `backup.sh` / `restore.sh` | Database backup/restore |
| `check-server-versions.sh` | Check HAPI/dependency versions |

---

## Documentation Files (20 total!)

### Core Documentation
| File | Description |
|------|-------------|
| `README.md` | General project overview |
| `ARCHITECTURE.md` | System architecture details |
| `PRODUCTION_STATUS.md` | What's implemented vs. planned |
| `KNOWN_LIMITATIONS.md` | What doesn't work |

### Requirements & Compliance
| File | Description |
|------|-------------|
| `REQUIREMENTS.md` | Functional requirements |
| `SDC_FORM_MANAGER_REQUIREMENTS.md` | SDC Form Manager conformance requirements (136 total) |
| `FORM_MANAGER_CAPABILITIES.md` | Current capabilities and workflows |
| `TEST_REQUIREMENTS_MAPPING.md` | Maps requirements to test cases (25.7% coverage) |

### Testing
| File | Description |
|------|-------------|
| `TESTING.md` | How to run tests |
| `TESTING_ACCOMPLISHMENTS.md` | Summary of test suite implementation |
| `MULTI_SERVER_TESTING.md` | Testing against HAPI, Aidbox, Azure, etc. |
| `api/tests/README.md` | Test suite structure |

### Implementation Guides
| File | Description |
|------|-------------|
| `IMPLEMENTING_ASSEMBLE_OPERATION.md` | Guide for adding $assemble (NOT implemented) |
| `ASSEMBLE_OPERATION_SUMMARY.md` | $assemble decision summary |
| `SDC_CONFIGURATION.md` | HAPI SDC configuration details |
| `FHIR_VALIDATOR_INTEGRATION.md` | Using HL7 FHIR Validator alongside pytest |

### Version Management
| File | Description |
|------|-------------|
| `FHIR_SERVER_VERSIONS.md` | Tracks HAPI/Aidbox versions for reproducibility |
| `VERSION_QUICK_REFERENCE.md` | Quick commands for version management |
| `VERSION_IN_METADATA_EXPLAINED.md` | Explains CapabilityStatement version fields |

### Strategic
| File | Description |
|------|-------------|
| `REFERENCE_IMPLEMENTATION_PLAN.md` | Vision: reduce PROM implementation costs to near-zero |

---

## What's Implemented

| Operation | Status | Implementation |
|-----------|--------|----------------|
| `$package` | ✅ Working | FastAPI + HAPI |
| `$localize` | ✅ Working | FastAPI |
| `$populate` | ✅ Working | HAPI Clinical Reasoning |
| `$extract` | ✅ Working | HAPI Clinical Reasoning |
| `$assemble` | ❌ Not implemented | Docs only |

---

## Quick Start

**Development (single HAPI):**
```bash
docker compose up -d
# API: http://localhost:8000
# HAPI: http://localhost:8080/fhir
```

**Run tests:**
```bash
cd api && pytest tests/ -v
```

---

## Key Decisions

- **HAPI FHIR** as primary server (pinned to v8.4.0)
- **SDC 3.0.0** Implementation Guide
- **MII PRO 2026.2.0** for German patient-reported outcomes
- **FastAPI** for custom operations not native to HAPI
- **$assemble** intentionally not implemented (marked as MAY/optional)
