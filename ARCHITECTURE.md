# Architecture

```
        clients (renderers, tests, consumer sites)
           │ FHIR REST                │ /api/questionnaires/...
           v                          v
┌─────────────────────────────┐  ┌─────────────────────────┐
│ Form Manager (HAPI 8.12)    │<─│ FastAPI sidecar (api/)  │
│ SDC, MII PRO, PRO Library,  │  │ $package, $localize,    │
│ PCOR-MII; CR on; Lucene     │  │ $compute-and-extract    │
└──────────────┬──────────────┘  └─────────────────────────┘
               │
       Postgres (dev) / H2 (test)
```

HAPI is the Form Manager. It stores and serves all content and runs `$populate`, `$extract` and `Library/$evaluate` through its Clinical Reasoning (CR) module. The sidecar adds only what HAPI lacks, and talks to HAPI over plain FHIR REST (`FHIR_BASE_URL`).

## Image build (`Dockerfile.form-manager`)

1. **Fetch stage.**
   - Downloads MII PRO and SDC from `packages.simplifier.net` and verifies their SHA-256.
   - Copies the vendored `local-packages/pcor-mii-${PCOR_MII_VERSION}.tgz`.
   - Applies the **draft→active patch** to SDC and PCOR-MII. For SD, CS, VS, SearchParameter, OperationDefinition, CapabilityStatement, StructureMap, ImplementationGuide and ConceptMap, a top-level `status: draft` is set to `active` and the package is re-packed.
   - Why the patch: HAPI's package installer skips draft resources. SDC 3.0.0 shipped everything as draft (4.0.0: 8 SDs), and PCOR-MII ships all its terminology as draft. Without the patch, the PCOR answerValueSets would not resolve.
   - MII PRO is used unchanged.
2. **Runtime stage.** Based on `hapiproject/hapi:v8.12.0-2@sha256:…` (distroless, bundles cqf-fhir-cr 4.13.0; tag and digest are both pinned so Renovate can propose updates).
   - Packages go to `/data/hapi/local-packages/`, including the vendored PRO Library tgz.
   - `hapi-config/application.yaml` goes to `/data/hapi/`.
   - `/data/hapi/lucene` is created empty and owned by the non-root user.
   - ENV: `HAPI_FHIR_CR_ENABLED=true` plus the version variables. `application.yaml` interpolates the package versions from them, and the sidecar reads `FORM_MANAGER_VERSION`.
   - OCI labels record the content versions.

`FORM_MANAGER_VERSION`, `PRO_LIBRARY_VERSION` and `PCOR_MII_VERSION` have no defaults. The Makefile and CI pass them from `versions.env`.

## HAPI configuration (`hapi-config/application.yaml`)

| Setting | Value / reason |
|---------|----------------|
| `implementationguides` | SDC, MII PRO, PCOR-MII and PRO Library from `file:///data/hapi/local-packages/…`, `STORE_AND_INSTALL`, `fetchDependencies: false`. No network at boot. |
| `cr.enabled` | `true`, for `$populate`, `$extract` and `$evaluate` |
| `validation.enabled` / `requests_enabled` | `false`. Validation belongs at publication time, and upstream Questionnaires have non-fatal issues that would block loading. |
| `spring.jpa.properties.hibernate.search.*` | Lucene on the local filesystem at `/data/hapi/lucene` |

ISiK and the Simplifier MII PRO ballot entries are commented out. ISiK fails snapshot generation at boot.

## Boot sequence

1. **Package installer.** HAPI installs only the canonical types from the packages: NamingSystem, CodeSystem, ValueSet, StructureDefinition, ConceptMap, SearchParameter, Subscription. It keys them on canonical **and** version, so several versions of one package coexist. `application.yaml` lists the current MII PRO version plus one entry per retained version, rendered at image build time by `hapi-scripts/render-application-yaml.py` from the `MII_PRO_RETAINED_VERSIONS` build-arg.
2. **Instance loader.** `hapi-scripts/load-instance-resources.sh` waits for `/metadata`, then PUTs the types the installer skips: Questionnaire, Library (incl. the CRMI release manifest), Provenance, ImplementationGuide, ObservationDefinition, TestScript.
   - The image is distroless, so the loader runs outside it. In compose it is the `pro-library-loader` service (alpine, mounts `./local-packages`). In CI and `make test-stack` it runs on the host over the image's own package dir (`docker cp` out of the container), never over the repo's `local-packages/`, which also holds stale tarballs.
   - **Version retention (Option A, 2026-10-19).** Older MII PRO versions are first-class content so QuestionnaireResponses pinned to `questionnaire|<old version>` keep resolving. The newest version per package (proper ordering: `2027.0.0` > `2027.0.0-ballot.1` > `2026.7.0`) is loaded by id and keeps the package ids. An older tarball is loaded only if declared in `RETAINED_PACKAGE_VERSIONS` (`<package>@<version>`, derived from `MII_PRO_RETAINED_VERSIONS`), because only then are its profiles and ValueSets installed too. Retained Questionnaires and Libraries are created by conditional update on `(url, version)` with the id stripped. ObservationDefinition (no canonical in R4) and Provenance cannot be versioned that way and are not loaded for retained versions: the current version's copy wins, so interpretation bands always come from the newest package.
   - The sidecar resolves an unversioned canonical to the **highest active version**, not the last written one, and resolves the unversioned `answerValueSet` references inside a Questionnaire to **that Questionnaire's own version** of the ValueSet (`PackageService.find_canonical` / `pick_version`). MII PRO pins none of its roughly 250 ValueSet references, so without this an old form would show the newest answer lists.
3. **Dependency installer (compose only).** `mii-pro-installer` runs `scripts/install-mii-pro.py`, which installs `hl7.fhir.r4.core` 4.0.1, `hl7.terminology` 6.4.0, SDC 4.0.0 and MII meta 2027.0.0-ballot via `$install-package`. This step needs registry access.

There is no HAPI healthcheck (no curl in a distroless image). Ordering relies on `depends_on`, the loader's `/metadata` polling, and a `sleep 30` before FastAPI starts.

## Terminology and `ValueSet/$expand`

The packages ship ValueSets **without expansion**. Clients expand `answerValueSet`s at runtime against this server. HAPI resolves concepts of DB-stored CodeSystems through Hibernate Search; without the Lucene index, `$expand` fails with `HSEARCH800001`.

- The index is the named volume `hapi_lucene`, next to `postgres_data`.
- If DB and index get out of sync, for example when one volume is deleted, run a `$reindex`.
- HAPI also caches installed package bytes in the DB. Re-vendoring a package under the same version has no effect on an existing DB until the package is removed or the DB is recreated.

## FastAPI sidecar (`api/`)

Routes under `/api/questionnaires` (`api/app/routers/questionnaires.py`):

| Route | Service | Notes |
|-------|---------|-------|
| `GET /`, `GET /{id}`, `POST /`, `PUT /{id}`, `DELETE /{id}`, `GET /search` | `fhir_client.py` | Proxy to HAPI |
| `$package`: `GET /{id}/$package`, `GET /$package?url=`, `POST /$package` | `package_service.py` | CRMI package (`crmi-package`; SDC defines no `$package`), collection Bundle: **outcome manifest first** (Library `asset-collection`, `crmi-manifestlibrary`: the Questionnaire as `composed-of`, every referenced dependency as `depends-on` with the exact packaged `url\|version`, messages as contained OperationOutcome via `cqf-messages`), then the Questionnaire, answerValueSets plus their CodeSystems, `cqf-library` Libraries (transitively), `targetStructureMap`s. Limits: 100 entries, 20 MB. |
| `$localize`: `GET /{id}/$localize`, `GET /$localize`, `POST /$localize`, `GET /{id}/$languages` | `localization_service.py` | One-language rendering of a multilingual Questionnaire |
| `POST /{id}/$compute-and-extract` | `scoring_extract_service.py` | See below |

Errors are FHIR `OperationOutcome`s (`application/fhir+json`; handlers in `main.py` map the HTTP status to the issue code, request-validation errors carry an `expression`). Also `POST /api/pro-ctcae/score` and `GET /health` (reports `FORM_MANAGER_VERSION`). Literal `$op` routes are sorted ahead of `/{id}`, so `$package` is never forwarded to HAPI as an id.

**`$compute-and-extract`** bridges a CR gap: HAPI CR does not evaluate `sdc-calculatedExpression` during `$populate` or `$extract`. The sidecar:

1. Reads the Questionnaire and resolves its `cqf-library`.
2. Calls `Library/$evaluate` for the subject.
3. Builds Observations generically from the content:
   - `item.code` becomes `Observation.code`.
   - The item's CQL `calculatedExpression` names the define.
   - `ObservationDefinition.qualifiedInterval` supplies the interpretation.
4. Returns them persisted (collection Bundle) or, with `persist=false`, as a transaction Bundle.

A new instrument needs only new content, no code change.

## clinical-reasoning >= 4.9 Parameters-Converter

**Fixed since base image `v8.12.0-2`** (cqf-fhir-cr 4.13.0); kept here because the sidecar's design follows from it. With `v8.12.0-1` (cqf-fhir-cr 4.9.0 / CQL engine 5.0.0), `Library/$evaluate` **without** an `expression` filter failed as soon as a public define returned a resource with backbone children. Here that is `MostRecentResponse`, a whole QuestionnaireResponse:

    Could not resolve inner FHIR type: QuestionnaireResponseItemAnswerComponent

The failure is in converting the result back into `Parameters` (`CqlFhirParametersConverter`), not in CQL evaluation. The same call with `?expression=PHQ9TotalScore&expression=…` returns correct values.

- **Workaround (implemented):** the sidecar requests only the defines named by the extract-flagged items' `calculatedExpression`. Keep this even after the upstream fix, because it also avoids serialising the whole QuestionnaireResponse per call.
- **Upstream:** fixed in clinical-reasoning 4.12.0 (PR #1089), in the image since `v8.12.0-2`. The strict-xfail tripwire fired as designed (2026-10-19) and is now the regression test `test_unfiltered_evaluate_works`: it fails if a base-image change brings the bug back.
- **PRO Library hygiene:** declare helper defines such as `MostRecentResponse` as `private define`.

## Consumer test network (`docker-compose.consumer-test.yml`)

An overlay on `docker-compose.yml`. It shows that a downstream site can receive the content through standard FHIR.

| Service | Role |
|---------|------|
| `consumer-hapi` + `consumer-db` | Second CR-enabled HAPI from the same image, host 8083, own Lucene volume |
| `consumer-mii-pro-installer` | Dependency packages, as on the producer |
| `consumer-crmi-sync` (`scripts/sync-from-crmi.py`) | Pulls the PRO Library CRMI release manifest `Library/release-0-1-4`, plus every `relatedArtifact` at its pinned version, from the producer |
| `consumer-pcor-sync` (`scripts/sync-from-ig.py`) | Pulls PCOR-MII by walking the IG's `definition.resource[]` (examples only with `SYNC_EXAMPLES=1`) |
| `lhc-forms` | nginx serving `lhc-forms/index.html` (lforms 42.2.2) on host 3004 |

The producer cannot store the PCOR-MII ImplementationGuide (HTTP 422, placeholder Bundles). The IG sync therefore takes the resource list from the vendored package, while the content still comes from the producer. The sync jobs are one-shot; re-run them with `make consumer-resync`.

Other compose files:

- `docker-compose.test.yml`: H2, HAPI 8081, FastAPI 8001, no loader service (`make test-stack` and CI run the loader from the host).
- `docker-compose.backup.yml`: optional Postgres backups.
- `docker-compose.aidbox.yml`: legacy and unmaintained. It runs a plain Aidbox without any of the content.

## mTLS front door (`deploy/mtls/`, `docker-compose.mtls.yml`)

Phase 1 of the access model: an nginx proxy is the only entry point; HAPI and the sidecar stay internal.

| Step | How |
|------|-----|
| Authentication | `ssl_verify_client on` against `ca.pem` (bundle of trusted CAs). No or untrusted certificate → 401 OperationOutcome. |
| Authorisation | SHA-1 certificate fingerprint must be in `allowlist.map` (`<fp> <site>;`), else 403. A valid certificate alone is not enough. |
| Identity | `X-Client-Site`, `-Cert-Fingerprint`, `-Cert-Subject` are set by nginx and overwrite client-sent values. The sidecar does not read them yet (licence gate = phase 2). |
| Read-only | Sites only read; content changes only through package updates (the loader writes over the internal network). `GET`/`HEAD` allowed; `POST` only for `ValueSet/$expand`, `$validate-code`, `CodeSystem/$lookup`/`$validate-code`/`$subsumes`, `Questionnaire/$package`/`$localize`. Everything else → 405. Blocked whatever the method (403): system operations `/fhir/$…`, `$populate`/`$extract`/`$compute-and-extract`/`$evaluate`/`$cql`/`$export`/`$expunge`/`$reindex` etc., patient-data types (QuestionnaireResponse, Observation, Patient, …), Swagger/api-docs. Rules match the decoded `$uri`, so `%24`-encodings do not bypass them. |
| Routing | One FHIR base: `/fhir/Questionnaire/{id}/$package\|$localize\|$languages` (id restricted to FHIR id syntax) and type-level `$package`/`$localize` go to the sidecar, all other `/fhir/` to HAPI, everything else 404. |
| Audit | Access log records site, fingerprint and request. |

**Test PKI:** `deploy/mtls/test-pki/` is committed on purpose (CA key discarded), so CI and local runs use the same certificates and a hard-coded allowlist: `site-a` allowed, `site-b` trusted but not listed, `rogue` from a foreign CA. Regenerate with `deploy/mtls/make-test-pki.sh`.

**Production guard:** unless `MTLS_ENV` is exactly `test` (any other value, typos included, counts as production), the entrypoint hook `10-forbid-test-pki.sh` refuses to start if the CA bundle contains the test CA (also inside a larger bundle) or the allowlist carries the TEST ONLY marker. A production stack mounts its own `ca.pem`, server certificate and allowlist.

## Deployment bundle (`deploy/`)

`deploy/docker-compose.yml` wires five services from published images: `db` (Postgres), `hapi` (Form Manager), `loader` (one-shot), `sidecar`, `proxy`. Only `proxy` publishes a port; the others share an `internal: true` network.

- **Images:** `Dockerfile.loader` builds FROM the Form Manager image of the same commit and copies its `/data/hapi/local-packages/`, so the loader and the server always agree on the content. `Dockerfile.proxy` bakes in `deploy/mtls/` (nginx config, production guard, test-CA reference) but no certificates, and defaults to `MTLS_ENV=production`. The sidecar image is `api/Dockerfile`.
- **Startup:** healthchecks instead of sleeps. HAPI uses the `HealthCheck` class shipped with `hapiproject/hapi` >= v8.12.0-2 (`/actuator/health`; the image is distroless). The loader and sidecar wait for a healthy HAPI, the proxy for HAPI and sidecar.
- **Publishing:** the `publish-components` job in `build-and-publish.yml` pushes the three images multi-arch after the Form Manager image, with the same tags. The dev `docker-compose.yml` builds the loader the same way (`additional_contexts: service:hapi-fhir`).
- **Test:** `scripts/test-deploy-bundle.sh` (CI job `deploy-bundle`, `make test-deploy`).

## CI and Renovate

| Workflow | Does |
|----------|------|
| `test.yml` | Unit layer first (no Docker), then: image build, test stack, loader over the image's package set, pytest `integration` + `content` + `upstream` with the sidecar in-process and a 75 % coverage gate. See [TESTING.md](TESTING.md).. Job `deploy-bundle`: the deployment bundle end to end. |
| `build-and-publish.yml` | Builds and smoke-tests the image, then pushes multi-arch to GHCR on the default branch and on `v*` tags. Smoke checks: ≥ 20 MII PRO SDs; PRO Library PHQ-9 + manifest; PCOR `UKHDEDP` + `pcor-item-dictionary`; `$expand`.. Then `publish-components` pushes `fhir-sdc-api`, `fhir-sdc-loader` and `fhir-sdc-proxy` with the same tags. |
| `auto-pin-pro-sha.yml` | On Renovate PRs that touch the Dockerfile: recomputes and commits `MII_PRO_SHA256` |
| `auto-vendor-pcor-mii.yml` | On Renovate PRs that touch `versions.env`: runs `scripts/refresh-pcor-mii.sh` and commits the tgz |
| `pages.yml` | Publishes `docs/` to GitHub Pages |

`renovate.json` runs Mondays before 6am (Europe/Berlin):

- **MII PRO:** Simplifier `dist-tags.latest`, matched on the Dockerfile ARG.
- **PCOR-MII:** gh-pages `package.manifest.json`, matched on `versions.env`.
- **SDC:** disabled, because a bump may need the patch list reviewed.
