# Testing

The pytest suite in `api/tests/` runs against a live stack: the Form Manager image plus the FastAPI sidecar. There are no mocked unit tests. Current CI result: **92 passed, 1 skipped, 2 xfailed**.

## Run locally (same steps as `.github/workflows/test.yml`)

```bash
pip install -r api/requirements.txt -r api/requirements-test.txt
make test-stack                      # HAPI :8081 (H2 in-memory) + FastAPI :8001, then runs the
                                     # instance loader over all packages (incl. those inside the image)
make test                            # pytest tests/sdc_compliance/ tests/integration/ -v --tb=short
docker compose -f docker-compose.test.yml down -v
```

- Endpoints come from `FHIR_BASE_URL` (default `http://localhost:8081/fhir`) and `API_BASE_URL` (default `http://localhost:8001`).
- The main stack also uses host port 8001, so do not run both at the same time.
- Coverage: add `--cov=app --cov-report=html`. The report lands in `api/htmlcov/`.
- Markers (`pytest.ini`, strict): `sdc_compliance`, `integration`, `failure_scenarios`, `slow`, `unit`.

## Layout

| Path | Covers |
|------|--------|
| `sdc_compliance/test_metadata.py` | CapabilityStatement presence, FHIR version, content |
| `sdc_compliance/test_operation_outcome.py` | OperationOutcome structure on errors |
| `sdc_compliance/test_package_operation.py` | Sidecar `$package`. See below. |
| `integration/test_questionnaire_crud.py` | CRUD and search through the sidecar, HAPI failure scenarios |
| `integration/test_pro_library_manifest.py` | PRO Library loaded at the pinned version; every CRMI manifest `relatedArtifact` resolves |
| `integration/test_calculated_expression_extract.py` | Locks in that HAPI CR's `$extract` / `$populate` do not evaluate `calculatedExpression` |
| `integration/test_compute_and_extract.py` | Sidecar `$compute-and-extract` end to end |
| `integration/test_evaluate_converter_regression.py` | CR >= 4.9 converter regression, plus the upstream tripwire |
| `integration/test_proctcae_scoring.py` | `/api/pro-ctcae/score` |
| `fixtures/sample_resources.py` | Synthetic resources for cases the shipped content does not cover |

`test_package_operation.py` tests:

- Bundle shape
- the Q→VS→CS chain on real MII PRO content
- Library inclusion
- missing, circular and deep dependencies
- a HAPI-native sentinel

Fixtures (`conftest.py`):

- Most tests address content shipped in the image by canonical URL (`pro_questionnaires`).
- Synthetic resources go through `clean_questionnaire` / `clean_valueset` / `clean_codesystem`, which delete them on teardown.
- The PRO Library version comes from `PRO_LIBRARY_VERSION` or `versions.env`; never hard-code it.
- `--fhir-server` / `--fhir-url` switch the target server. Only HAPI with the bundled content is maintained.

## Expected non-passes

| Test | Kind | Meaning |
|------|------|---------|
| `test_unfiltered_evaluate_upstream_tripwire` | strict xfail | Flips once HAPI ships CR >= 4.12. Then update [ARCHITECTURE.md](ARCHITECTURE.md#clinical-reasoning--49-parameters-converter). |
| `test_hapi_native_package_is_partial` | xfail | HAPI's own `$package` still 500s on MII PRO PHQ-9 |
| `test_create_questionnaire_missing_required_field` | skip | Request-time validation is off |

## What CI checks

- **`test.yml`** (push/PR to master, main, develop): image build, test stack, loader, the full pytest suite with coverage. The Codecov upload is non-blocking.
- **`build-and-publish.yml`**: boots the freshly built image on its own before pushing to GHCR. It asserts:
  - ≥ 20 MII PRO StructureDefinitions at the pinned version
  - PRO Library PHQ-9 and release manifest
  - PCOR-MII `UKHDEDP` Questionnaire and `pcor-item-dictionary` CodeSystem
  - a working `ValueSet/$expand`
