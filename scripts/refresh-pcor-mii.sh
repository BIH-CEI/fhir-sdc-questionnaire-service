#!/usr/bin/env bash
# Refresh the vendored PCOR-MII IG package from the official IG build.
#
# PCOR-MII has no package registry release yet; the only artefact is
# https://bih-cei.github.io/PCOR-MII/package.tgz, which gh-pages rebuilds on
# every deploy (same version, different bytes). That is why we vendor it as
# local-packages/pcor-mii-<version>.tgz and refresh deliberately.
#
# Usage:
#   scripts/refresh-pcor-mii.sh            # re-vendor the version pinned in versions.env;
#                                          # fails if upstream moved to another version
#   scripts/refresh-pcor-mii.sh --bump     # take whatever version upstream publishes and
#                                          # update PCOR_MII_VERSION in versions.env
#
# Env:
#   PCOR_MII_PACKAGE_URL   override the source tgz (default: gh-pages package.tgz)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSIONS_ENV="${REPO_ROOT}/versions.env"
PKG_DIR="${REPO_ROOT}/local-packages"
URL="${PCOR_MII_PACKAGE_URL:-https://bih-cei.github.io/PCOR-MII/package.tgz}"
BUMP=0
[ "${1:-}" = "--bump" ] && BUMP=1

log() { echo "[refresh-pcor-mii] $*" >&2; }

pinned=$(grep -E '^PCOR_MII_VERSION=' "${VERSIONS_ENV}" | head -1 | cut -d= -f2)
[ -n "${pinned}" ] || { log "ERROR: PCOR_MII_VERSION not found in versions.env"; exit 1; }

tmp=$(mktemp -d)
trap 'rm -rf "${tmp}"' EXIT

log "Downloading ${URL}"
curl -sfL "${URL}" -o "${tmp}/package.tgz"
tar -xzf "${tmp}/package.tgz" -C "${tmp}" package/package.json

name=$(jq -r '.name // empty' "${tmp}/package/package.json")
upstream=$(jq -r '.version // empty' "${tmp}/package/package.json")
[ "${name}" = "pcor-mii" ] || { log "ERROR: unexpected package name '${name}'"; exit 1; }
[ -n "${upstream}" ] || { log "ERROR: package.json has no version"; exit 1; }
log "Upstream: ${name}@${upstream} (pinned: ${pinned})"

if [ "${upstream}" != "${pinned}" ]; then
    if [ "${BUMP}" -ne 1 ]; then
        log "ERROR: upstream is ${upstream}, versions.env pins ${pinned}. Re-run with --bump to move the pin."
        exit 1
    fi
    sed -i.bak -E "s|^PCOR_MII_VERSION=.*|PCOR_MII_VERSION=${upstream}|" "${VERSIONS_ENV}"
    rm -f "${VERSIONS_ENV}.bak"
    log "versions.env: PCOR_MII_VERSION ${pinned} -> ${upstream}"
fi

target="${PKG_DIR}/pcor-mii-${upstream}.tgz"
if [ -f "${target}" ] && cmp -s "${tmp}/package.tgz" "${target}"; then
    log "${target#"${REPO_ROOT}/"} already identical — nothing to do."
    exit 0
fi
if [ -f "${target}" ]; then
    # gh-pages re-publishes under an unchanged version; the content may differ
    # (new/changed resources), not just the build timestamp. Review the diff.
    log "WARN: ${target#"${REPO_ROOT}/"} exists with different bytes — upstream re-published ${upstream} without a version bump."
fi
cp "${tmp}/package.tgz" "${target}"
log "Wrote ${target#"${REPO_ROOT}/"} (sha256 $(shasum -a 256 "${target}" | awk '{print $1}'))"
