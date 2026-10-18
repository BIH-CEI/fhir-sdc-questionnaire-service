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

.PHONY: up build down logs ps test test-stack consumer-up consumer-down consumer-logs consumer-resync refresh-pcor-mii bump-pcor-mii

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

# Same sequence as CI (test.yml): boot, then PUT the resource types HAPI's
# installer skips. MII PRO + SDC tarballs only exist inside the image, so they
# are copied out next to the vendored ones before the loader runs.
test-stack:
	docker compose -f docker-compose.test.yml up -d --build
	until curl -sf http://localhost:8081/fhir/metadata -o /dev/null; do sleep 3; done
	mkdir -p local-packages-merged
	cp -f local-packages/*.tgz local-packages-merged/
	docker cp hapi-fhir-test:/data/hapi/local-packages/. local-packages-merged/
	HAPI_URL=http://localhost:8081/fhir PKGS_DIR=./local-packages-merged ./hapi-scripts/load-instance-resources.sh

test:
	cd api && python3 -m pytest tests/sdc_compliance/ tests/integration/ -v --tb=short

# Downstream consumer test network: producer Form Manager + a separate
# CR-enabled HAPI that re-receives the SDC + MII PRO + PRO Library + PCOR-MII content,
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
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml logs -f --tail=200 consumer-hapi consumer-crmi-sync consumer-pcor-sync lhc-forms

# Re-run the CRMI + PCOR-MII pulls on demand (e.g. after bumping MANIFEST_ID
# in the overlay or after editing a sync script). The services have
# restart:no, so `up` won't re-fire them; force one-shot runs.
consumer-resync:
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml run --rm consumer-crmi-sync
	docker compose -f docker-compose.yml -f docker-compose.consumer-test.yml run --rm consumer-pcor-sync

# PCOR-MII: the vendored local-packages/pcor-mii-<v>.tgz is the official IG
# build from gh-pages (rebuilt on every deploy, so bytes are pinned by
# vendoring). Refresh deliberately:
#
#   make refresh-pcor-mii   # re-vendor the pinned version; fails if upstream moved
#   make bump-pcor-mii      # follow upstream and update PCOR_MII_VERSION in versions.env
refresh-pcor-mii:
	scripts/refresh-pcor-mii.sh

bump-pcor-mii:
	scripts/refresh-pcor-mii.sh --bump
