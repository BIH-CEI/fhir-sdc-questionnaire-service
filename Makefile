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

.PHONY: up build down logs ps test test-stack

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
