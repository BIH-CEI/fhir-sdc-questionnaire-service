# Deployment bundle

Runs the Form Manager from published images only. No repo checkout or build on the server. Only the mTLS proxy is reachable from outside.

```
site systems ──mTLS──▶ proxy :443 ─┬─▶ sidecar (FastAPI) ─┐
                                   └─▶ hapi (Form Manager) ◀┘──▶ db (Postgres)
                       loader (one-shot) ──▶ hapi
```

| Service | Image | Role |
|---------|-------|------|
| `proxy` | `ghcr.io/bih-cei/fhir-sdc-proxy` | nginx: client-certificate check, allowlist, one FHIR base (`/fhir/`) |
| `hapi` | `ghcr.io/bih-cei/fhir-sdc-form-manager` | HAPI with SDC, MII PRO, PRO Library and PCOR-MII baked in |
| `sidecar` | `ghcr.io/bih-cei/fhir-sdc-api` | `$package` (CRMI), `$localize`, `$compute-and-extract` |
| `loader` | `ghcr.io/bih-cei/fhir-sdc-loader` | PUTs Questionnaires, Libraries etc. after boot (the installer skips them), then exits |
| `db` | `postgres:15-alpine` | Persistence |

All four project images are published with the same tags (`sha-<short>`, `form-manager-<version>`, `mii-pro-<version>`, `latest`), and the loader carries exactly the package set of the Form Manager image it was built from. Pin one tag for all of them via `FM_TAG`.

## Run

```bash
cp .env.example .env          # set FM_TAG, POSTGRES_PASSWORD, PROXY_PORT
# put ca.pem, server.pem, server.key, allowlist.map into ./pki/ (see pki/README.md)
docker compose up -d
docker compose ps             # db, hapi, sidecar healthy; loader exited 0
```

The first start takes a few minutes: HAPI installs the packages, then the loader runs. For about a minute after a fresh start, `ValueSet/$expand` can return empty expansions while HAPI pre-expands ValueSets in the background.

## Access

- **No or untrusted client certificate:** 401 OperationOutcome.
- **Trusted certificate not on the allowlist:** 403.
- **Allowlisted:** everything under `/fhir/`. The sidecar operations (`/fhir/Questionnaire/{id}/$package`, `$localize`, `$languages`, `$compute-and-extract`, type-level `$package`/`$localize`) go to the sidecar, everything else to HAPI.
- **Audit:** the proxy's access log records site, certificate fingerprint and request.

Add a site: append `<fingerprint> <site>;` to `pki/allowlist.map`, then `docker compose exec proxy nginx -s reload`.

## Safety nets

- `MTLS_ENV=production` (the default in the proxy image and in `.env.example`): the proxy refuses to start with the TEST-ONLY PKI from `deploy/mtls/test-pki/`, also when the test CA is part of a larger bundle.
- `db`, `hapi`, `sidecar` and `loader` sit on an internal network without a route outside; only `proxy` publishes a port.
- Keep `postgres_data` and `hapi_lucene` together: losing one without the other needs a `$reindex`.

## Operations

| Task | Command |
|------|---------|
| Update | set the new `FM_TAG` in `.env`, then `docker compose pull && docker compose up -d` |
| Re-run the loader | `docker compose run --rm loader` |
| Logs | `docker compose logs -f proxy hapi sidecar` |
| Backup | dump `db` (e.g. `docker compose exec db pg_dump -U hapi hapi > backup.sql`), plus the `hapi_lucene` volume or a `$reindex` after restore |

## Not covered yet

- Per-site licence gate: the sidecar does not read the `X-Client-*` identity headers yet.
- Certificate revocation lists (nginx `ssl_crl`).
- Authentication inside the backend network: HAPI and the sidecar trust the proxy.

Tested end to end in CI (`scripts/test-deploy-bundle.sh`, locally `make test-deploy`).
