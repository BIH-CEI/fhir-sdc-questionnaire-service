# Agent Instructions

FHIR SDC Form Manager: a HAPI FHIR 8.12 image with SDC, MII PRO, PRO Library and PCOR-MII baked in, plus a FastAPI sidecar for `$package`, `$localize` and `$compute-and-extract`.
Human docs: `README.md` (overview, versions, limitations), `ARCHITECTURE.md`, `TESTING.md`.

## Where things are

| Path | What |
|------|------|
| `Dockerfile.form-manager` | Image build: digest-pinned HAPI, SHA-pinned MII PRO/SDC (ARGs), vendored PRO Library/PCOR-MII, draft→active patch |
| `versions.env` | `FORM_MANAGER_VERSION`, `PRO_LIBRARY_VERSION`, `PCOR_MII_VERSION` |
| `hapi-config/application.yaml` | Package install list, CR on, Lucene, validation off |
| `hapi-scripts/load-instance-resources.sh` | Post-boot loader for Questionnaire/Library/… |
| `api/app/` | FastAPI sidecar: `routers/questionnaires.py`, `services/{package,localization,scoring_extract}_service.py` |
| `api/tests/` | pytest layers `unit/`, `integration/` (sidecar in-process), `content/`, `upstream/` (HAPI behaviour, strict xfails); `support/`, `fixtures/`, `conftest.py`. See `TESTING.md`. |
| `docker-compose.yml` / `.test.yml` / `.consumer-test.yml` | Dev stack (8095/8001) / test stack (8081/8001) / consumer overlay (8083, LHC-Forms 3004) |
| `scripts/` | `refresh-pcor-mii.sh`, `sync-from-crmi.py`, `sync-from-ig.py`, `install-mii-pro.py`, backup/restore. The ISiK scripts, `install_mii_package.py` and `check-server-versions.*` are legacy. |
| `local-packages/` | Vendored package tarballs |
| `deploy/` | Deployment bundle (published images, mTLS proxy); `Dockerfile.loader`, `Dockerfile.proxy` build its extra images |
| `docs/` | Strategy docs (not published) |
| `ig/` | Implementation Guide (SUSHI + IG Publisher, BIH template fetched by `ig/fetch-template.sh`), published to GitHub Pages by `pages.yml` |
| `.github/workflows/` | `test.yml`, `build-and-publish.yml`, `auto-pin-pro-sha.yml`, `auto-vendor-pcor-mii.yml`, `pages.yml` |

## Commands

```bash
make build && make up            # dev stack (needs .env from .env.example)
make test-unit                   # pure-function tests + loader version-ordering check, no Docker
make test-stack && make test     # test stack (loader included), then integration/content/upstream
make consumer-up                 # consumer HAPI + CRMI/IG sync + LHC-Forms
make refresh-pcor-mii            # re-vendor PCOR-MII; make bump-pcor-mii to follow upstream
```

## Gotchas

- **`deploy/mtls/test-pki/` holds committed TEST-ONLY keys** (un-ignored in `.gitignore`). Never put real keys there or use them outside the test stack; nginx refuses them when `MTLS_ENV=production`.
- **HAPI's installer skips `status: draft` resources.** SDC and PCOR-MII are patched draft→active in `Dockerfile.form-manager`. A new package with draft content needs the same patch.
- **HAPI's installer skips Questionnaire, Library, Provenance, ImplementationGuide, ObservationDefinition and TestScript.** `load-instance-resources.sh` PUTs them after boot. A stack without the loader has no Questionnaires. Only the newest package version keeps its ids; older versions are loaded only when declared in `RETAINED_PACKAGE_VERSIONS` (derived from the `MII_PRO_RETAINED_VERSIONS` Dockerfile ARG, which also installs their terminology). Run the loader over the image's package dir, not over `local-packages/`.
- **Retained MII PRO versions must be vendored.** `MII_PRO_RETAINED_VERSIONS` in `Dockerfile.form-manager` names versions whose tarball is in `local-packages/`; the build fails otherwise. ObservationDefinitions are never retained (no canonical in R4).
- **Tests: the sidecar runs in-process.** `api_client` drives the FastAPI app via httpx's ASGI transport against the HAPI container; that is what makes coverage real. Expected failures are strict xfails that must flip when upstream changes, see `TESTING.md`.
- **HAPI caches package bytes in the DB.** A package re-vendored under the same version does not take effect on an existing DB. Recreate it (`docker compose down -v`).
- **`ValueSet/$expand` needs the Lucene index** (Hibernate Search, volume `hapi_lucene`). Packages ship no expansions. If DB and index diverge, run `$reindex`. Right after boot HAPI re-stores its TermValueSets and pre-expands them in the background; until then `$expand` answers 200 with an **empty** expansion. The content tests poll for up to 90 s instead of asserting once.
- **Versions live only in `versions.env` and the Dockerfile ARGs.** Do not hard-code them in config, compose or tests.
- **Keep passing `expression=` to `Library/$evaluate`.** The CR 4.9 converter bug is fixed since base image `v8.12.0-2`, but filtering avoids serialising whole QuestionnaireResponses. See ARCHITECTURE.md "clinical-reasoning >= 4.9 Parameters-Converter".
- **Validation is off by design.** Do not "fix" tests by turning it on.
- The parent `interop-prototypes/` is a container, not a repo. Run `git` and `bd` inside this directory.

## Non-interactive shell

`cp`, `mv` and `rm` may be aliased to `-i` and hang waiting for a prompt. Use `cp -f`, `mv -f`, `rm -f` / `rm -rf`. Use `-o BatchMode=yes` for `ssh`/`scp`, `apt-get -y`, and `HOMEBREW_NO_AUTO_UPDATE=1` for brew.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->
