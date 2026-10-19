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

# Upstream MII PRO pins live only in Dockerfile.form-manager (Renovate bumps
# them). Derived here for the loader: retained versions are declared as
# "<package>@<version>" so older tarballs are loaded only when their
# terminology is installed too.
MII_PRO_RETAINED_VERSIONS := $(shell sed -nE 's/^ARG MII_PRO_RETAINED_VERSIONS="?([^"]*)"?$$/\1/p' Dockerfile.form-manager)
RETAINED_PACKAGE_VERSIONS := $(foreach v,$(MII_PRO_RETAINED_VERSIONS),de.medizininformatikinitiative.kerndatensatz.pros@$(v))
export RETAINED_PACKAGE_VERSIONS

.PHONY: test-mtls up build down logs ps test test-unit test-stack consumer-up consumer-down consumer-logs consumer-resync refresh-pcor-mii bump-pcor-mii

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
# The image's own package dir is the declared content set (current + retained
# MII PRO, SDC, PCOR-MII, PRO Library) — copy it out, never mix in the repo's
# local-packages/ (which also holds stale tarballs).
test-stack:
	docker compose -f docker-compose.test.yml up -d --build
	until curl -sf http://localhost:8081/fhir/metadata -o /dev/null; do sleep 3; done
	rm -rf local-packages-image && mkdir -p local-packages-image
	docker cp hapi-fhir-test:/data/hapi/local-packages/. local-packages-image/
	HAPI_URL=http://localhost:8081/fhir PKGS_DIR=./local-packages-image \
	  RETAINED_PACKAGE_VERSIONS="$(RETAINED_PACKAGE_VERSIONS)" ./hapi-scripts/load-instance-resources.sh

test-unit:
	cd api && python3 -m pytest tests/unit -q
	bash hapi-scripts/test-loader-version-order.sh

# mTLS front door on top of the test stack (run test-stack first). Uses the
# committed TEST-ONLY PKI; see deploy/mtls/.
test-mtls:
	docker compose -f docker-compose.test.yml -f docker-compose.mtls.yml up -d --no-deps mtls-proxy
	until curl -sk https://localhost:8443/ -o /dev/null; do sleep 2; done
	scripts/test-mtls.sh

test:
	cd api && python3 -m pytest tests/integration/ tests/content/ tests/upstream/ -v --tb=short

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
