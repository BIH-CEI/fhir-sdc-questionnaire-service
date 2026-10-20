#!/usr/bin/env bash
# Run the acceptance battery (acceptance/) against a deployed endpoint.
#
#   scripts/acceptance-test.sh https://formmanager.example.org site.pem site.key [server-ca.pem]
#
# or set FM_ENDPOINT, FM_CLIENT_CERT, FM_CLIENT_KEY (and optionally
# FM_SERVER_CA, FM_UNLISTED_CERT/KEY, FM_EXPECT_*) and call it without
# arguments. Extra pytest arguments: ACCEPTANCE_ARGS="-m 'not latency'".
#
# Writes acceptance-report.xml (JUnit) into the current directory; exit code is
# pytest's (0 = all passed).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ $# -ge 1 ] && export FM_ENDPOINT="$1"
[ $# -ge 3 ] && export FM_CLIENT_CERT="$2" FM_CLIENT_KEY="$3"
[ $# -ge 4 ] && export FM_SERVER_CA="$4"

: "${FM_ENDPOINT:?usage: $0 <endpoint> <client-cert> <client-key> [server-ca]}"
: "${FM_CLIENT_CERT:?client certificate missing}"
: "${FM_CLIENT_KEY:?client key missing}"

# The suite runs from acceptance/, so make file arguments absolute.
abspath() { [ -n "$1" ] && (cd "$(dirname "$1")" && echo "$PWD/$(basename "$1")"); }
for v in FM_CLIENT_CERT FM_CLIENT_KEY FM_SERVER_CA FM_UNLISTED_CERT FM_UNLISTED_KEY; do
    [ -n "${!v:-}" ] && export "$v=$(abspath "${!v}")"
done

PY="${ACCEPTANCE_PYTHON:-python3}"
if ! "$PY" -c "import pytest, httpx" 2>/dev/null; then
    venv="${ACCEPTANCE_VENV:-$ROOT/.venv-acceptance}"
    [ -x "$venv/bin/python" ] || "$PY" -m venv "$venv"
    "$venv/bin/pip" install -q -r "$ROOT/acceptance/requirements.txt"
    PY="$venv/bin/python"
fi

report="${ACCEPTANCE_REPORT:-$PWD/acceptance-report.xml}"
cd "$ROOT/acceptance"
# shellcheck disable=SC2086
exec "$PY" -m pytest -p no:cacheprovider --junitxml="$report" ${ACCEPTANCE_ARGS:-} .
