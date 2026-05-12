# FHIR SDC Form Manager

A containerized FHIR Form Manager (HAPI FHIR + SDC IG + MII PRO IG, baked into the image) and the validation infrastructure that proves it actually conforms to the SDC Form Manager capability statement.

## What this repo is

Two things, both shipped as code:

1. **A Form Manager container** — `ghcr.io/BIH-CEI/fhir-sdc-form-manager`. HAPI FHIR with the SDC 3.0.0 IG and MII PRO IG already loaded at build time, ready to serve `$populate`, `$extract`, `$package`, `$localize`. No first-boot IG download, no terminology bootstrapping, no flaky cold-start.
2. **Validation infrastructure** — CI smoke tests, SDC compliance tests, integration tests, FHIR validator integration. Every published image has been booted and asserted against the SDC Form Manager capability statement before the tag was pushed.

What this repo is **not**: a workshop, a reference clinic, a demo deployment. Those experiments lived here previously and have been removed.

## The container image

```bash
docker pull ghcr.io/BIH-CEI/fhir-sdc-form-manager:latest
docker run -p 8080:8080 ghcr.io/BIH-CEI/fhir-sdc-form-manager:latest
# FHIR endpoint: http://localhost:8080/fhir/metadata
```

Tags published on every `master` push:

| Tag | Meaning |
|-----|---------|
| `latest` | Tip of `master` |
| `mii-pro-<version>` | Pinned to a specific MII PRO release (currently `mii-pro-2026.3.0`) |
| `sha-<short>` | Reproducible pointer to a git commit |
| `v*` | Release tags |

Multi-arch: `linux/amd64`, `linux/arm64`.

### What's baked in

| Component | Version | Source |
|-----------|---------|--------|
| HAPI FHIR | 8.4.0 (pinned by digest) | `hapiproject/hapi` |
| SDC IG | 3.0.0 | `hl7.fhir.uv.sdc` (status patched `draft`→`active` so HAPI accepts it; see `Dockerfile.form-manager`) |
| MII PRO IG | 2026.3.0 | `de.medizininformatikinitiative.kerndatensatz.pros` |

All upstream tarballs are SHA-256-verified during the image build. Renovate + `.github/workflows/auto-pin-pro-sha.yml` keep MII PRO pins fresh.

## Validation infrastructure

Living in `api/tests/` and `.github/workflows/build-and-publish.yml`:

- **CI smoke test** — every PR boots the freshly built image, hits `/fhir/metadata`, and asserts ≥ 20 MII PRO `StructureDefinition`s loaded. If the image won't boot or the IG didn't install, the build fails.
- **SDC compliance tests** (`api/tests/sdc_compliance/`) — assertions against the [SDC Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html): metadata, OperationOutcome shapes, `$package`.
- **Integration tests** (`api/tests/integration/`) — Questionnaire CRUD, calculated-expression `$extract`, PRO-CTCAE scoring round-trip.
- **FHIR Validator integration** — see `FHIR_VALIDATOR_INTEGRATION.md` for running the official HL7 validator alongside the test suite.
- **Coverage map** — `TEST_REQUIREMENTS_MAPPING.md` tracks which SDC Form Manager requirements are covered by which tests.

Run the full suite locally against a built image:

```bash
docker compose -f docker-compose.test.yml up -d
cd api && pytest tests/sdc_compliance/ tests/integration/ -v
```

## Local development

Full stack (Form Manager + Postgres + FastAPI sidecar):

```bash
cp .env.example .env
docker compose up -d
# HAPI:    http://localhost:8080/fhir
# FastAPI: http://localhost:8000
```

The FastAPI sidecar in `api/` adds operations HAPI doesn't ship natively:

- `Questionnaire/$package` — bundle a Questionnaire with all its dependencies (ValueSets, CodeSystems, Libraries). HAPI's native `$package` is partial; see `api/tests/sdc_compliance/test_package_operation.py` for the divergence.
- `Questionnaire/$localize` — produce a translated render of a multilingual Questionnaire.
- PRO-CTCAE scoring endpoint.

| Endpoint | Implementation |
|----------|----------------|
| `$populate`, `$extract` | HAPI (Clinical Reasoning module, baked-in) |
| `$package` (full) | FastAPI sidecar |
| `$localize` | FastAPI sidecar |
| `$assemble` | Not implemented — see `ASSEMBLE_OPERATION_SUMMARY.md` for why |

## SDC capabilities

Implements the [SDC Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html):

- **SHALL resources**: `Questionnaire`, `ValueSet` (+ `$expand`, `$validate-code`), `CodeSystem` (+ `$lookup`), `Library` — all CRUD via HAPI.
- **Operations**: `$populate` ✅ · `$extract` ✅ · `$package` ✅ · `$assemble` ❌ (intentionally out of scope, optional in spec).

## Repo map

| Path | Purpose |
|------|---------|
| `Dockerfile.form-manager` | The container build — fetch + verify IGs, patch SDC status, install at boot |
| `docker-compose.yml` | Local dev stack |
| `docker-compose.test.yml` | CI / local test stack |
| `api/` | FastAPI sidecar + test suite |
| `hapi-config/`, `hapi-scripts/` | HAPI YAML config + entrypoint scripts |
| `scripts/install-mii-pro.py`, `verify-mii-pro-load.py` | IG install / verify helpers |
| `.github/workflows/build-and-publish.yml` | Build → smoke → compliance tests → publish to GHCR |
| `.github/workflows/auto-pin-pro-sha.yml` | Renovate-style auto-pin of MII PRO SHA-256 |

## Further reading

- `ARCHITECTURE.md` — system design
- `PRODUCTION_STATUS.md` — what's implemented vs planned
- `KNOWN_LIMITATIONS.md` — what doesn't work
- `SDC_FORM_MANAGER_REQUIREMENTS.md` — the 136-requirement conformance checklist
- `TEST_REQUIREMENTS_MAPPING.md` — requirements → test coverage
- `REFERENCE_IMPLEMENTATION_PLAN.md` — vision: drive PROM implementation cost toward zero
- `FHIR_SERVER_VERSIONS.md` — pinned versions for reproducibility

## References

- [FHIR SDC Specification](https://build.fhir.org/ig/HL7/sdc/)
- [MII Kerndatensatz PRO](https://simplifier.net/medizininformatikinitiative-modulpro)
- [HAPI FHIR](https://hapifhir.io/)
