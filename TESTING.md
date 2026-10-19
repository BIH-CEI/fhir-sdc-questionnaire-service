# Testing

Four layers, one pytest tree under `api/tests/`. Markers are strict (`pytest.ini`).

| Layer | Path | Needs | Answers |
|-------|------|-------|---------|
| **unit** | `tests/unit/` | nothing | Is the logic right? Pure functions: severity bands, translation extraction, dependency walking, version ordering, PRO-CTCAE parsing. Milliseconds. |
| **integration** | `tests/integration/` | HAPI | Does the sidecar produce the right thing against real server behaviour? The FastAPI app runs **in-process** (httpx ASGI transport), so `--cov=app` measures real lines and error paths can be injected via `dependency_overrides`. |
| **content** | `tests/content/` | HAPI | Does the image ship what the pins say? MII PRO current + retained versions, PRO Library manifest, PCOR-MII incl. the draft→active patch, a live `ValueSet/$expand`. Also the publish workflow's smoke test. |
| **upstream** | `tests/upstream/` | HAPI | What does HAPI itself do? `$extract`/`$populate` ignore `calculatedExpression`, the (fixed) CR ≥ 4.9 converter bug as a regression test, the crashing native `$package`, the CapabilityStatement. Expected failures are **strict xfails**: when HAPI improves, the run goes red on purpose. |

`sdc_compliance` is a cross-cutting marker for tests that map to an SDC Form Manager requirement. One file, `tests/integration/test_sidecar_container.py`, hits the containerized sidecar on port 8001 to prove the shipped image boots. The consumer stack (`make consumer-up`, LHC-Forms on 3004) is manual end-to-end only.

## Run locally (same steps as `.github/workflows/test.yml`)

```bash
pip install -r api/requirements.txt -r api/requirements-test.txt
make test-unit                       # unit layer + loader version-ordering check, no Docker
make test-stack                      # HAPI :8081 (H2 in-memory) + sidecar :8001, then the loader
                                     # over the image's own package set (current + retained MII PRO)
make test                            # pytest tests/integration tests/content tests/upstream
docker compose -f docker-compose.test.yml down -v
```

- HAPI: `FHIR_BASE_URL` (default `http://localhost:8081/fhir`) or `--fhir-url`.
- Sidecar: in-process by default. Set `API_BASE_URL` to test a running sidecar black-box instead (no coverage, no dependency overrides).
- Coverage: `cd api && pytest tests/integration tests/content tests/upstream --cov=app --cov-report=html`. CI fails below 75 %. Report in `api/htmlcov/`.
- The main stack also uses host port 8001, so do not run both at the same time.

## Fixtures (`conftest.py`)

- `fhir_server`: httpx client against HAPI. `api_client`: the sidecar (in-process or HTTP).
- `pro_questionnaires` (session): ids of MII PRO content by canonical, fails loudly if the image is missing it.
- `clean_questionnaire` / `clean_valueset` / `clean_codesystem` / `clean_library`: create synthetic resources, delete on teardown.
- `test_subject`: a throwaway Patient; its QuestionnaireResponses and Observations are deleted on teardown, so repeated runs do not accumulate data.
- Versions come from `versions.env` (`PRO_LIBRARY_VERSION`, `PCOR_MII_VERSION`) and the Dockerfile ARGs (`MII_PRO_VERSION`, `MII_PRO_RETAINED_VERSIONS`). Never hard-code them.
- `tests/support/pro_library.py`: PHQ-9 / SF-4a QuestionnaireResponse builders shared by integration and upstream tests.
- `ValueSet/$expand` assertions poll (up to 90 s): shortly after boot HAPI is still pre-expanding and returns empty expansions. Seen as a flaky publish smoke test on master after PR #2.

## Expected non-passes

All are `strict=True`: an unexpected pass fails the run, which is the point.

| Test | Why |
|------|-----|
| `upstream/test_hapi_native_package::test_hapi_native_package_is_crmi_conformant` | HAPI's own `$package` 500s on MII PRO (NPE at `PackageVisitor.java:276`: no CRMI outcome manifest for non-Library roots). Flips when it returns a CRMI package; then reconsider the sidecar layer. |
| `integration/test_proctcae_scoring::test_score_returns_composite_grades` | No package ships `Library/PRO_CTCAE`; the endpoint cannot score. Ship the CQL or remove the router (bead). |
| `integration/test_questionnaire_crud::test_create_missing_required_field_is_rejected` | No request-time validation by design; no sidecar schema check yet. |
| `integration/test_questionnaire_crud::test_update_removes_omitted_fields` | PUT sets attributes one by one; omitted fields survive (bead). |
| `integration/test_questionnaire_crud::test_search_total_is_server_total_not_page_length` | `Bundle.total` is the page length (bead). |
| `integration/test_questionnaire_crud::test_search_free_text` | `q` maps to `_content`, which needs HAPI full-text indexing (off) → 500 (bead). |

## What CI checks

- **`test.yml`** (push/PR to master, main, develop): unit layer first (no Docker), then image build, test stack, loader over the image's package set, and `pytest tests/integration tests/content tests/upstream` with a 75 % coverage gate. The HTML report is an artifact.
- **mTLS front door** (step in `test.yml`, locally `make test-mtls` after `make test-stack`): `scripts/test-mtls.sh` checks no/foreign/unlisted/allowed certificates (401/401/403/200), the FHIR routing to sidecar vs. HAPI, and that the production guard refuses the test PKI but accepts a stand-in production PKI.
- **Acceptance battery** (`acceptance/`, `scripts/acceptance-test.sh <endpoint> <cert> <key> [ca]`): checks a *deployed* endpoint through its mTLS proxy (transport, access, read-only, content, operations, latency) and writes a JUnit report. See [acceptance/README.md](acceptance/README.md). CI runs it inside the bundle test.
- **Deployment bundle** (job `deploy-bundle` in `test.yml`, locally `make test-deploy`): `scripts/test-deploy-bundle.sh` builds the four images, starts `deploy/docker-compose.yml` with the TEST-ONLY PKI, waits for the loader, runs `scripts/test-mtls.sh` against it, and checks that the proxy image's default refuses the test PKI.
- **`build-and-publish.yml`**: boots the freshly built image on its own, runs the loader and `pytest tests/content` against it before pushing to GHCR. Same tests as above, so PRs and the publish gate cannot drift apart.
