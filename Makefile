# Thin wrapper that makes versions.env the single source of truth for
# "our" versions (FORM_MANAGER_VERSION, PRO_LIBRARY_VERSION) without
# requiring every caller to remember --env-file flags.
#
#   make up          # docker compose up -d, with versions.env in scope
#   make build       # docker compose build, ditto
#   make test        # run the pytest integration suite against the stack
#
# CI runs equivalent commands directly with `set -a; source versions.env;
# set +a` early in each job — see .github/workflows/test.yml.

# Export every var defined in versions.env to recipe environments.
include versions.env
export

.PHONY: up build down logs ps test test-stack consumer-up consumer-down consumer-logs

up:
	docker compose up -d

build:
	docker compose build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

test-stack:
	docker compose -f docker-compose.test.yml up -d --build

test:
	cd api && pytest tests/sdc_compliance/ tests/integration/ -v --tb=short

# Downstream consumer test network: producer Form Manager + a separate
# CR-enabled HAPI that re-receives the SDC + MII PRO + PRO Library content,
# plus a self-hosted LHC-Forms widget for end-to-end SDC testing.
#
#   Producer HAPI:           http://localhost:8095/fhir
#   Consumer HAPI:           http://localhost:8083/fhir
#   LHC-Forms test harness:  http://localhost:3004
consumer-up:
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml up -d

consumer-down:
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml down

consumer-logs:
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml logs -f --tail=200 consumer-hapi consumer-crmi-sync lhc-forms

# Re-run the CRMI pull on demand (e.g. after bumping MANIFEST_ID in the
# overlay or after editing sync-from-crmi.py). The service has restart:no,
# so `up` won't re-fire it; force a one-shot run.
consumer-resync:
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml run --rm consumer-crmi-sync
