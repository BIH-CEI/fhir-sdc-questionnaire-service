The service runs from published container images; a server needs no source checkout and no build. Images are Linux containers for `linux/amd64` and `linux/arm64`.

| Service | Image | Role |
|---------|-------|------|
| `proxy` | `ghcr.io/bih-cei/fhir-sdc-proxy` | nginx: client certificates, allowlist, routing; the only published port |
| `hapi` | `ghcr.io/bih-cei/fhir-sdc-form-manager` | HAPI FHIR with all content |
| `sidecar` | `ghcr.io/bih-cei/fhir-sdc-api` | Sidecar operations |
| `loader` | `ghcr.io/bih-cei/fhir-sdc-loader` | One-shot: loads Questionnaires, Libraries etc. after boot (HAPI's package installer skips them) |
| `db` | `postgres:18-alpine` | Persistence |

All four project images are published with the same tags (`sha-<short>`, `form-manager-<version>`, `mii-pro-<version>`, `latest`); the loader carries exactly the package set of the Form Manager image it was built from. Pin one tag for all of them.

### Run

Requirements: Linux with Docker Engine and the Compose plugin (v2).

    # from the repository's deploy/ folder
    cp .env.example .env     # FM_TAG, POSTGRES_PASSWORD, EDGE_NETWORK (no published port)
    # ca.pem, server.pem, server.key, allowlist.map into ./pki/
    docker compose up -d
    docker compose ps        # db, hapi, sidecar healthy; loader exited 0

First start takes a few minutes: HAPI installs the packages, then the loader runs.

### Built-in safety nets

- **Network:** `db`, `hapi`, `sidecar` and `loader` sit on an internal network without a route outside.
- **Test PKI refused:** the proxy image defaults to `MTLS_ENV=production` and then refuses to start with the test PKI committed in the repository (also inside a larger CA bundle).
- **Startup order:** healthchecks, not sleeps. HAPI is checked through the `HealthCheck` class of the HAPI image.

Every pull request starts the complete bundle with the test PKI in CI and runs the access and routing checks against it.
