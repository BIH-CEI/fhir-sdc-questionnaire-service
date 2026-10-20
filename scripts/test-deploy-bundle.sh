#!/usr/bin/env bash
# End-to-end test of the deployment bundle (deploy/docker-compose.yml):
# builds the four images locally (unless SKIP_BUILD=1), starts the bundle with
# the committed TEST-ONLY PKI and MTLS_ENV=test, waits for the loader, then runs
# scripts/test-mtls.sh against the bundle's proxy. Finally checks that the
# proxy image's default (MTLS_ENV=production) refuses the test PKI.
#
#   scripts/test-deploy-bundle.sh          # make test-deploy
#
# Env: FM_REGISTRY (default local), FM_TAG (default bundle-test),
#      PROXY_PORT (default 9443), SKIP_BUILD=1, KEEP=1 (leave the stack running)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
set -a; . ./versions.env; set +a

REG="${FM_REGISTRY:-local}"
TAG="${FM_TAG:-bundle-test}"
RETAINED=$(grep -E '^ARG MII_PRO_RETAINED_VERSIONS=' Dockerfile.form-manager | cut -d= -f2 | tr -d '"')
RETAINED_PKGS=$(for v in $RETAINED; do printf 'de.medizininformatikinitiative.kerndatensatz.pros@%s ' "$v"; done)

log() { echo "[test-deploy-bundle] $*"; }

if [ "${SKIP_BUILD:-0}" != 1 ]; then
    log "building images $REG/*:$TAG"
    docker build -q -f Dockerfile.form-manager \
        --build-arg FORM_MANAGER_VERSION="$FORM_MANAGER_VERSION" \
        --build-arg PRO_LIBRARY_VERSION="$PRO_LIBRARY_VERSION" \
        --build-arg PCOR_MII_VERSION="$PCOR_MII_VERSION" \
        -t "$REG/fhir-sdc-form-manager:$TAG" . >/dev/null
    docker build -q -t "$REG/fhir-sdc-api:$TAG" api >/dev/null
    docker build -q -f Dockerfile.loader \
        --build-arg FORM_MANAGER_IMAGE="$REG/fhir-sdc-form-manager:$TAG" \
        --build-arg RETAINED_PACKAGE_VERSIONS="$RETAINED_PKGS" \
        -t "$REG/fhir-sdc-loader:$TAG" . >/dev/null
    docker build -q -f Dockerfile.proxy -t "$REG/fhir-sdc-proxy:$TAG" . >/dev/null
fi

export FM_REGISTRY="$REG" FM_TAG="$TAG" PROXY_PORT="${PROXY_PORT:-9443}" \
       PKI_DIR=./mtls/test-pki MTLS_ENV=test POSTGRES_PASSWORD=bundle-test \
       EDGE_NETWORK=fm-bundle-test-edge
# The host's ingress network stands in as a plain network; the port overlay
# lets the checks reach the proxy from here.
C=(docker compose -p fm-bundle-test -f deploy/docker-compose.yml -f deploy/docker-compose.port.yml)
"${C[@]}" down -v >/dev/null 2>&1 || true
docker network create "$EDGE_NETWORK" >/dev/null 2>&1 || true
cleanup() {
    [ "${KEEP:-0}" = 1 ] && return
    "${C[@]}" down -v >/dev/null 2>&1 || true
    docker network rm "$EDGE_NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT

log "starting bundle (proxy on :$PROXY_PORT)"
"${C[@]}" up -d >/dev/null

log "waiting for the loader to finish"
for _ in $(seq 1 120); do
    st=$("${C[@]}" ps -a --format '{{.Service}} {{.State}} {{.ExitCode}}' | awk '$1=="loader"{print $2" "$3}')
    case "$st" in
        "exited 0") break ;;
        exited*) log "loader failed: $st"; "${C[@]}" logs loader | tail -30; exit 1 ;;
    esac
    sleep 5
done
[ "$st" = "exited 0" ] || { log "loader did not finish: ${st:-not started}"; "${C[@]}" ps -a; exit 1; }
"${C[@]}" logs loader 2>&1 | grep -E -- "---|WARN" | grep -v ImplementationGuide | sed 's/^/  /' | head -20

until curl -sk "https://localhost:$PROXY_PORT/" -o /dev/null; do sleep 2; done
"${C[@]}" ps --format '  {{.Service}}: {{.Status}}'

MTLS_URL="https://localhost:$PROXY_PORT" MTLS_PROXY_CONTAINER="$("${C[@]}" ps -q proxy)" \
    scripts/test-mtls.sh

log "acceptance battery against the bundle"
PKI="$ROOT/deploy/mtls/test-pki"
FM_UNLISTED_CERT="$PKI/site-b.pem" FM_UNLISTED_KEY="$PKI/site-b.key" \
ACCEPTANCE_REPORT="${ACCEPTANCE_REPORT:-$ROOT/acceptance-report.xml}" \
    scripts/acceptance-test.sh "https://localhost:$PROXY_PORT" "$PKI/site-a.pem" "$PKI/site-a.key" "$PKI/ca.pem"

log "proxy image default refuses the test PKI"
name="fm-proxy-default-$$"
docker run -d --name "$name" \
    -v "$ROOT/deploy/mtls/test-pki/ca.pem:/etc/nginx/mtls/ca.pem:ro" \
    -v "$ROOT/deploy/mtls/test-pki/server.pem:/etc/nginx/mtls/server.pem:ro" \
    -v "$ROOT/deploy/mtls/test-pki/server.key:/etc/nginx/mtls/server.key:ro" \
    -v "$ROOT/deploy/mtls/test-pki/allowlist.map:/etc/nginx/mtls/allowlist.map:ro" \
    "$REG/fhir-sdc-proxy:$TAG" >/dev/null
sleep 3
running=$(docker inspect -f '{{.State.Running}}' "$name")
refused=$(docker logs "$name" 2>&1 | grep -c REFUSING || true)
docker rm -f "$name" >/dev/null
if [ "$running" = false ] && [ "$refused" -gt 0 ]; then
    log "ok: image default MTLS_ENV=production refused the test PKI"
else
    log "FAIL: proxy image with test PKI and default env is running=$running"; exit 1
fi
log "bundle test passed"
