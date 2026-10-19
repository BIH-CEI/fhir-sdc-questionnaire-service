How the service and its content are kept current, and what an operator does routinely.

### Versioning and releases

| What | Where it is pinned | How it is updated |
|------|--------------------|-------------------|
| Service (`FORM_MANAGER_VERSION`) | `versions.env` | Manually, on functional changes |
| HAPI FHIR base image | `Dockerfile.form-manager` (`HAPI_BASE`, tag + digest) | Renovate proposes new images |
| MII PRO (current, retained) | `Dockerfile.form-manager` (version + SHA-256) | Renovate; a workflow re-pins the SHA |
| SDC | `Dockerfile.form-manager` | Manually (a draft→active patch may need review) |
| PRO Library | `versions.env` + vendored package | Manually |
| PCOR-MII | `versions.env` + vendored package | Renovate (a workflow vendors the package) or `make bump-pcor-mii` |

Every change runs through CI before merge:
- unit tests,
- integration and content tests against a real server (coverage gate 75 %),
- tests that pin HAPI's own behaviour,
- the full deployment bundle with the test PKI.

Every merge to `master` publishes all four images with the same tags.

**Upstream sentinels:** tests in `api/tests/upstream/` record known HAPI behaviour as strict expected failures, e.g. the crash of HAPI's native `$package`. When a HAPI update changes that behaviour, the build fails on purpose, so the workaround can be revisited deliberately.

### Updating a server

1. Choose the new tag (`sha-<short>` of the merge commit, or `form-manager-<version>`).
2. Set `FM_TAG` in `deploy/.env`.
3. `docker compose pull && docker compose up -d`. The loader runs again and updates the content.

Content of a version that was already installed under the same version number is cached in HAPI's database. If a package is re-published without a version bump, recreate the database (or remove the package) to pick it up.

### Routine tasks

| Task | How |
|------|-----|
| Add or remove a site | Edit `pki/allowlist.map` (`<fingerprint> <site>;`), then `docker compose exec proxy nginx -s reload` |
| Rotate the server certificate | Replace `pki/server.pem`/`server.key`, reload nginx |
| Change trusted CAs | Edit `pki/ca.pem`, reload nginx |
| Backup | `pg_dump` of `db`; keep the `hapi_lucene` volume with it or run `$reindex` after a restore |
| Re-run the loader | `docker compose run --rm loader` |
| Logs and audit | `docker compose logs proxy` (site, fingerprint, request per line) |

### Not production-ready yet

- **Per-site licence gate:** every allowlisted site sees all content.
- **No revocation checking** for client certificates.
- **Write operations** through the FHIR base are not restricted per site beyond the allowlist.
- **No request-time validation** on the server; content is validated at publication time.

### Ownership

Maintained by BIH-CEI. Issues and changes: [GitHub repository](https://github.com/BIH-CEI/fhir-sdc-questionnaire-service). Content issues belong to their source: MII PRO module (ballot portal of HL7 Deutschland), PRO Library, PCOR-MII.
