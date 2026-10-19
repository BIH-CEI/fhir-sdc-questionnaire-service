#!/usr/bin/env bash
# Checks the mTLS front door (docker-compose.mtls.yml) and its production guard.
#
#   docker compose -f docker-compose.test.yml -f docker-compose.mtls.yml up -d
#   (load instance resources, e.g. via make test-stack)
#   scripts/test-mtls.sh
#
# Env: MTLS_URL (default https://localhost:8443)

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PKI="$ROOT/deploy/mtls/test-pki"
URL="${MTLS_URL:-https://localhost:8443}"
PHQ9="https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire/mii-qst-pro-phq-9"
fails=0

BODY=$(mktemp)
req() {  # $1 client (none|site-a|site-b|rogue), $2 path, rest: extra curl args -> status; body in $BODY
    local client="$1" path="$2"; shift 2
    local auth=()
    [ "$client" != none ] && auth=(--cert "$PKI/$client.pem" --key "$PKI/$client.key")
    curl -s --cacert "$PKI/ca.pem" ${auth[@]+"${auth[@]}"} -o "$BODY" -w '%{http_code}' "$@" "$URL$path"
}

check() {  # $1 description, $2 expected status, $3 jq filter that must be true (or ""), $4.. req args
    local desc="$1" want="$2" filter="$3"; shift 3
    local status
    status=$(req "$@")
    if [ "$status" = "$want" ] && { [ -z "$filter" ] || jq -e "$filter" "$BODY" >/dev/null 2>&1; }; then
        echo "  ok    $desc ($status)"
    else
        echo "  FAIL  $desc: got $status, want $want${filter:+ and $filter}: $(head -c 200 "$BODY" | tr -d '\n')"
        fails=$((fails + 1))
    fi
}

echo "== access"
check "no client certificate is rejected"        401 '.issue[0].code=="login"'     none   /fhir/metadata
check "certificate from a foreign CA is rejected" 401 '.issue[0].code=="login"'     rogue  /fhir/metadata
check "trusted but not allowlisted site -> 403"   403 '.issue[0].code=="forbidden"' site-b /fhir/metadata
check "allowlisted site reaches HAPI"             200 '.resourceType=="CapabilityStatement"' site-a /fhir/metadata
check "only /fhir/ is exposed"                    404 '.issue[0].code=="not-found"' site-a /api/questionnaires/

echo "== routing (one FHIR base)"
req site-a "/fhir/Questionnaire?url=$PHQ9&_elements=id" >/dev/null
qid=$(jq -r '.entry[0].resource.id // empty' "$BODY")
if [ -z "$qid" ]; then
    echo "  FAIL  PHQ-9 not found via the proxy (instance resources loaded?)"; fails=$((fails + 1))
else
    check "instance \$package -> sidecar (HAPI's native one 500s)" 200 '.resourceType=="Bundle" and .type=="collection"' site-a "/fhir/Questionnaire/$qid/\$package"
    check "type-level \$package?url= -> sidecar"                    200 '.resourceType=="Bundle"' site-a "/fhir/Questionnaire/\$package?url=$PHQ9"
    check "\$languages -> sidecar"                                  200 ''                        site-a "/fhir/Questionnaire/$qid/\$languages"
    check "plain read -> HAPI"                                      200 '.resourceType=="Questionnaire"' site-a "/fhir/Questionnaire/$qid"
fi
check "ValueSet/\$expand -> HAPI" 200 '.resourceType=="ValueSet"' site-a \
    "/fhir/ValueSet/\$expand?url=https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"

echo "== spoofing"
log_line=$(docker logs mtls-proxy 2>&1 | grep -c 'site="site-a"')
check "a forged X-Client-Site header does not bypass the allowlist" 403 '' site-b /fhir/metadata -H "X-Client-Site: site-a"
[ "$log_line" -gt 0 ] && echo "  ok    access log records the certificate's site" || { echo "  FAIL  no site in access log"; fails=$((fails + 1)); }

echo "== production guard"
guard() {  # $1 description, $2 expected (refuse|start), $3 ca.pem, $4 allowlist
    local name="mtls-guard-$$" logs
    docker rm -f "$name" >/dev/null 2>&1
    docker run -d --name "$name" -e MTLS_ENV=production \
        -e HAPI_UPSTREAM=127.0.0.1:1 -e SIDECAR_UPSTREAM=127.0.0.1:1 \
        -v "$ROOT/deploy/mtls/nginx-mtls.conf:/etc/nginx/templates/default.conf.template:ro" \
        -v "$ROOT/deploy/mtls/10-forbid-test-pki.sh:/docker-entrypoint.d/10-forbid-test-pki.sh:ro" \
        -v "$ROOT/deploy/mtls/forbidden-test-ca.b64:/etc/nginx/forbidden-test-ca.b64:ro" \
        -v "$3:/etc/nginx/mtls/ca.pem:ro" -v "$4:/etc/nginx/mtls/allowlist.map:ro" \
        -v "$PKI/server.pem:/etc/nginx/mtls/server.pem:ro" -v "$PKI/server.key:/etc/nginx/mtls/server.key:ro" \
        nginx:1.27-alpine >/dev/null
    sleep 3
    local running; running=$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)
    logs=$(docker logs "$name" 2>&1)
    docker rm -f "$name" >/dev/null 2>&1
    if { [ "$2" = refuse ] && [ "$running" = false ] && echo "$logs" | grep -q "REFUSING"; } ||
       { [ "$2" = start ] && [ "$running" = true ]; }; then
        echo "  ok    $1"
    else
        echo "  FAIL  $1 (running=$running): $(echo "$logs" | grep -m1 -E 'REFUSING|emerg|accepted')"; fails=$((fails + 1))
    fi
}
tmp=$(mktemp -d); trap 'rm -rf "$tmp" "$BODY"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$tmp/prod-ca.key" -subj "/CN=Stand-in production CA" \
    -days 1 -out "$tmp/prod-ca.pem" 2>/dev/null
echo "0000000000000000000000000000000000000000 site-x;" > "$tmp/prod-allowlist.map"
cat "$tmp/prod-ca.pem" "$PKI/ca.pem" > "$tmp/bundle-with-test-ca.pem"
guard "refuses the test CA"                     refuse "$PKI/ca.pem"                 "$tmp/prod-allowlist.map"
guard "refuses a bundle that includes the test CA" refuse "$tmp/bundle-with-test-ca.pem" "$tmp/prod-allowlist.map"
guard "refuses the test allowlist"              refuse "$tmp/prod-ca.pem"            "$PKI/allowlist.map"
guard "starts with a non-test CA and allowlist" start  "$tmp/prod-ca.pem"            "$tmp/prod-allowlist.map"

echo
if [ "$fails" -eq 0 ]; then echo "mTLS checks: all passed"; else echo "mTLS checks: $fails failed"; exit 1; fi
