#!/bin/sh
# nginx entrypoint hook (/docker-entrypoint.d/): refuse to start a production
# proxy with the committed TEST-ONLY PKI or the hard-coded test allowlist.
#
#   MTLS_ENV=test        the test PKI is allowed (test stacks only)
#   anything else        (incl. unset, "production", typos) treated as
#                        production: exit 1 if
#     - the CA bundle contains the test CA (also inside a larger bundle), or
#     - the allowlist carries the TEST ONLY marker written by make-test-pki.sh
#
# The nginx image has no openssl CLI, so the test CA is recognised by its
# base64 body (forbidden-test-ca.b64, written by make-test-pki.sh).

set -eu
# Fail closed: only the explicit value "test" skips the checks.
[ "${MTLS_ENV:-production}" = "test" ] && { echo "10-forbid-test-pki: MTLS_ENV=test, test PKI allowed"; exit 0; }

CA=/etc/nginx/mtls/ca.pem
ALLOWLIST=/etc/nginx/mtls/allowlist.map
FORBIDDEN=/etc/nginx/forbidden-test-ca.b64

fail() { echo "10-forbid-test-pki: REFUSING TO START (MTLS_ENV=${MTLS_ENV:-unset}, treated as production): $*" >&2; exit 1; }

[ -s "$CA" ] || fail "$CA missing or empty"
[ -s "$ALLOWLIST" ] || fail "$ALLOWLIST missing or empty"
[ -s "$FORBIDDEN" ] || fail "$FORBIDDEN missing - cannot check for the test CA"

if tr -d '\n\r' < "$CA" | grep -qF "$(tr -d '\n\r' < "$FORBIDDEN")"; then
    fail "the CA bundle contains the TEST-ONLY test CA"
fi
if grep -q "TEST ONLY" "$ALLOWLIST"; then
    fail "the allowlist is the TEST-ONLY test allowlist"
fi
echo "10-forbid-test-pki: production PKI accepted"
