#!/bin/bash
# Unit check for the loader's version ordering (no HAPI needed).
# Run: bash hapi-scripts/test-loader-version-order.sh
set -euo pipefail
cd "$(dirname "$0")"

# Pull ver_key / pkg_meta / latest_for out of the loader without executing the load.
eval "$(sed -n '/^ver_key()/,/^}/p; /^pkg_meta()/,/^}/p; /^latest_for()/,/^}/p' load-instance-resources.sh)"

fail=0
expect_gt() {  # $1 > $2
    if [[ "$(ver_key "$1")" > "$(ver_key "$2")" ]]; then
        echo "ok   $1 > $2"
    else
        echo "FAIL $1 should rank above $2 (keys: $(ver_key "$1") vs $(ver_key "$2"))"; fail=1
    fi
}
expect_gt 2027.0.0 2027.0.0-ballot.1     # release beats its own pre-release
expect_gt 2027.0.0-ballot.1 2026.7.0     # pre-release of a newer line beats older release
expect_gt 2026.10.0 2026.7.0             # numeric, not lexical
expect_gt 2027.0.0-ballot.2 2027.0.0-ballot.1
expect_gt 0.1.4 0.1.3

# Package metadata must be readable with this platform's tar (GNU or bsdtar),
# otherwise every tarball is treated as "latest" and older versions overwrite
# the current one by id.
PKGS_DIR=../local-packages
for t in "${PKGS_DIR}"/*.tgz; do
    read -r n v <<<"$(pkg_meta "$t")"
    if [ -n "$n" ] && [ -n "$v" ]; then
        echo "ok   $(basename "$t") -> $n $v"
    else
        echo "FAIL $(basename "$t"): package.json not readable with $(tar --version | head -1)"; fail=1
    fi
done
latest=$(latest_for de.medizininformatikinitiative.kerndatensatz.pros)
case "$latest" in
    2027.*) echo "ok   latest MII PRO among vendored tarballs: $latest" ;;
    *) echo "FAIL latest MII PRO resolved to '$latest'"; fail=1 ;;
esac
exit $fail
