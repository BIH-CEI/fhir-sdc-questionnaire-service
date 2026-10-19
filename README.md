# FHIR SDC Form Manager

A containerized FHIR SDC Form Manager. It is HAPI FHIR with the SDC IG, MII PRO, the BIH-CEI PRO Library and PCOR-MII baked into the image. A small FastAPI sidecar adds the SDC operations HAPI does not provide. CI boots every image and checks it against the [SDC Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html) before it is published to `ghcr.io/bih-cei/fhir-sdc-form-manager` (amd64/arm64).

## Quick start

```bash
cp .env.example .env
make build && make up
```

| Service | URL |
|---------|-----|
| Form Manager (HAPI) | http://localhost:8095/fhir (`HAPI_PORT` overrides) |
| FastAPI sidecar | http://localhost:8001 (OpenAPI at `/docs`) |
| Consumer HAPI (`make consumer-up`) | http://localhost:8083/fhir |
| LHC-Forms renderer (`make consumer-up`) | http://localhost:3004 |

| Make target | Does |
|-------------|------|
| `up` / `down` / `build` / `logs` / `ps` | Main stack: Postgres, Form Manager, instance loader, dependency installer, FastAPI |
| `test-stack` / `test` | Test stack (H2, HAPI 8081) and pytest. See [TESTING.md](TESTING.md). |
| `consumer-up` / `consumer-down` / `consumer-logs` / `consumer-resync` | Consumer test network: a second HAPI pulls content from the producer |
| `refresh-pcor-mii` / `bump-pcor-mii` | Re-vendor PCOR-MII at the pinned version, or follow upstream and bump `versions.env` |

All targets load `versions.env`. A bare `docker run` of the image serves terminology and profiles only. Questionnaires and Libraries are added by the loader after boot (see [ARCHITECTURE.md](ARCHITECTURE.md)).

## Bundled content and versions

| Content | Version | Pinned in | Updated by |
|---------|---------|-----------|------------|
| Form Manager itself | 0.2.0 | `versions.env` `FORM_MANAGER_VERSION` | Manually |
| HAPI FHIR | 8.12.0 (image `v8.12.0-2`, cqf-fhir-cr 4.13.0; tag + digest) | `Dockerfile.form-manager` `HAPI_BASE` | Renovate (custom regex manager) |
| SDC `hl7.fhir.uv.sdc` | 4.0.0 | Dockerfile ARGs `SDC_VERSION` / `SDC_SHA256` | Manually (Renovate disabled) |
| MII PRO `de.medizininformatikinitiative.kerndatensatz.pros` | 2027.0.0-ballot.1 (ballot) | Dockerfile ARGs `MII_PRO_VERSION` / `MII_PRO_SHA256` | Renovate; `auto-pin-pro-sha.yml` re-pins the SHA |
| PRO Library `bih-cei.fhir.pro-library` | 0.1.4 | `versions.env` + vendored tgz in `local-packages/` | Manually |
| PCOR-MII `pcor-mii` | 0.3.0 (gh-pages build of 2026-10-14) | `versions.env` + vendored tgz in `local-packages/` | Renovate (`auto-vendor-pcor-mii.yml`), or `make bump-pcor-mii` |

How the upstream packages are pinned:

- SDC and MII PRO are downloaded from Simplifier at build time and checked against their SHA-256.
- PCOR-MII is vendored because its only artefact, the gh-pages `package.tgz`, is rebuilt with new bytes under the same version. `make refresh-pcor-mii` warns when that happens.

Image tags:

- `latest`, `mii-pro-<v>` and `form-manager-<v>` on the default branch
- `sha-<short>` on every published build
- the git tag name for `v*` tags

## Operations

| Operation | Status | Implemented by |
|-----------|--------|----------------|
| CRUD and search: Questionnaire, ValueSet, CodeSystem, Library, … | Working | HAPI |
| `ValueSet/$expand`, `$validate-code`, `CodeSystem/$lookup` | Working | HAPI (`$expand` needs the Lucene index) |
| `Questionnaire/$populate`, `QuestionnaireResponse/$extract` | Working | HAPI Clinical Reasoning |
| `Library/$evaluate` (CQL scoring) | Working | HAPI Clinical Reasoning |
| `Questionnaire/$package` (CRMI `crmi-package`; SDC defines none) | Working | FastAPI: CRMI outcome manifest first, then Questionnaire + dependencies. HAPI's native one crashes on MII PRO content (NPE, no manifest) |
| `Questionnaire/$localize` | Working | FastAPI |
| `Questionnaire/$compute-and-extract` | Working | FastAPI: evaluates scoring CQL and builds Observations |
| `Questionnaire/$assemble` | Intentionally not implemented | It is optional (MAY) in SDC, and no bundled Questionnaire is modular |

## Deployment readiness

Fine for demos and internal staging. **Not production-ready:**

- No authentication. The sidecar calls HAPI unauthenticated (`api/app/services/fhir_client.py`, `authorization=None`) and exposes its own endpoints without auth.
- CORS is `*` in the sidecar (`api/app/config.py`) and in HAPI's default `.env.example`.
- `docker-compose.yml` is a dev setup:
  - Postgres port 5433 is exposed and uses default credentials.
  - uvicorn runs with `--reload` and a bind-mounted source tree.
  - Startup ordering relies on sleeps.
  - No restart policies, no TLS, no reverse proxy.
- Request-time validation is off on purpose.
- mTLS access is tested (`docker-compose.mtls.yml`: client certificates, allowlist, one FHIR base), but there is no production stack yet, and the per-site licence gate is not implemented.

## Known limitations

- **PCOR-MII ImplementationGuide cannot be stored** (HTTP 422).
  - Cause: its example-Bundle references create placeholder Bundles without `type`, because `auto_create_placeholder_reference_targets=true`.
  - Effect: the Questionnaires and terminology load fine. The consumer IG sync reads the resource list from the vendored package instead.
- **HAPI caches package bytes in the DB.** An existing database keeps its old copy of a package re-vendored under the same version (e.g. PCOR-MII 0.3.0 from before the draft→active patch). Recreate the DB (`docker compose down -v`) or remove the package.
- **Validation is off.** HAPI accepts structurally invalid resources. Validate at publication time, e.g. with the HL7 validator CLI.
- **HAPI's native `$package` crashes** on almost all MII PRO / PCOR-MII Questionnaires (NPE in cqf-fhir-cr up to 4.13.0); the sidecar's CRMI-conformant `$package` is used instead.

## Documentation

| File | Content |
|------|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Image build, boot sequence, `$expand`, sidecar, consumer network, CI |
| [TESTING.md](TESTING.md) | Running the tests, layout, expected xfails, CI checks |
| [AGENTS.md](AGENTS.md) | Instructions for coding agents (paths, commands, gotchas, workflow) |
| [docs/VISION.md](docs/VISION.md), [docs/REFERENCE_IMPLEMENTATION_PLAN.md](docs/REFERENCE_IMPLEMENTATION_PLAN.md), [docs/FUTURE_IDEAS.md](docs/FUTURE_IDEAS.md) | Strategy |
| [docs/ARTIFACT_METADATA_POLICY.md](docs/ARTIFACT_METADATA_POLICY.md) | Artifact metadata policy |
| [docs/SDC_FORM_MANAGER_REQUIREMENTS.md](docs/SDC_FORM_MANAGER_REQUIREMENTS.md) | SDC Form Manager requirement checklist |

References: [FHIR SDC](https://build.fhir.org/ig/HL7/sdc/) · [MII KDS PRO](https://simplifier.net/medizininformatikinitiative-modulpro) · [PCOR-MII](https://bih-cei.github.io/PCOR-MII/) · [PRO Library](https://github.com/BIH-CEI/pro-library) · [HAPI FHIR](https://hapifhir.io/)
