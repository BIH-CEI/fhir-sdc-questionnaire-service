#!/bin/bash
# Post-startup loader: PUT the resource types HAPI's PackageInstallerSvc
# skips on auto-install (Questionnaire, Library, Provenance, ImplementationGuide).
#
# HAPI's PackageInstallerSvcImpl only handles NamingSystem, CodeSystem,
# ValueSet, StructureDefinition, ConceptMap, SearchParameter, Subscription.
# Anything else in an installed FHIR Package is silently ignored — so the
# pro-library PHQ-9, the release manifest Library, and the Provenance never
# land in HAPI unless we PUT them ourselves after the server is reachable.
#
# This script:
#   1. Waits for HAPI metadata endpoint
#   2. For each tarball in /data/hapi/local-packages/*.tgz:
#      - extracts to /tmp/<pkgname>
#      - for each .json that's Questionnaire / Library / Provenance / ImplementationGuide:
#          PUT /fhir/<type>/<id>
#   3. Logs per-package per-type counts

set -euo pipefail

HAPI_URL="${HAPI_URL:-http://localhost:8080/fhir}"
PKGS_DIR="${PKGS_DIR:-/data/hapi/local-packages}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-180}"
LOAD_TYPES=(Questionnaire Library Provenance ImplementationGuide)

log() { echo "[load-instance-resources] $*" >&2; }

log "Waiting up to ${WAIT_TIMEOUT}s for HAPI at ${HAPI_URL}/metadata ..."
deadline=$(($(date +%s) + WAIT_TIMEOUT))
until curl -sfo /dev/null "${HAPI_URL}/metadata"; do
    if [ "$(date +%s)" -ge "$deadline" ]; then
        log "ERROR: HAPI not reachable after ${WAIT_TIMEOUT}s — giving up"
        exit 1
    fi
    sleep 3
done
log "HAPI reachable. Beginning instance-resource load."

if ! command -v jq >/dev/null 2>&1; then
    log "ERROR: jq not installed in image; cannot extract resource ids"
    exit 1
fi

shopt -s nullglob
for tarball in "${PKGS_DIR}"/*.tgz; do
    pkg_name=$(basename "${tarball}" .tgz)
    workdir="/tmp/load-${pkg_name}"
    rm -rf "${workdir}" && mkdir -p "${workdir}"
    tar xzf "${tarball}" -C "${workdir}"

    log "--- ${pkg_name} ---"
    # Per-type counters — flat variables for bash 3.x portability (macOS)
    count_Questionnaire=0
    count_Library=0
    count_Provenance=0
    count_ImplementationGuide=0

    for jsonfile in "${workdir}/package/"*.json; do
        [ -f "${jsonfile}" ] || continue
        basename_jf=$(basename "${jsonfile}")
        [ "${basename_jf}" = "package.json" ] && continue
        [ "${basename_jf}" = ".index.json" ] && continue

        rt=$(jq -r '.resourceType // empty' "${jsonfile}")
        rid=$(jq -r '.id // empty' "${jsonfile}")

        # Only handle types HAPI's installer skips
        case " ${LOAD_TYPES[*]} " in
            *" ${rt} "*) ;;
            *) continue ;;
        esac

        [ -z "${rid}" ] && { log "  WARN: ${basename_jf} has no id, skipping"; continue; }

        http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -X PUT "${HAPI_URL}/${rt}/${rid}" \
            -H "Content-Type: application/fhir+json" \
            --data-binary @"${jsonfile}")

        if [[ "${http_code}" =~ ^2 ]]; then
            case "${rt}" in
                Questionnaire)        count_Questionnaire=$((count_Questionnaire + 1)) ;;
                Library)              count_Library=$((count_Library + 1)) ;;
                Provenance)           count_Provenance=$((count_Provenance + 1)) ;;
                ImplementationGuide)  count_ImplementationGuide=$((count_ImplementationGuide + 1)) ;;
            esac
        else
            log "  WARN: PUT ${rt}/${rid} returned HTTP ${http_code}"
        fi
    done

    [ "${count_Questionnaire}" -gt 0 ]       && log "  Questionnaire: loaded ${count_Questionnaire}"
    [ "${count_Library}" -gt 0 ]             && log "  Library: loaded ${count_Library}"
    [ "${count_Provenance}" -gt 0 ]          && log "  Provenance: loaded ${count_Provenance}"
    [ "${count_ImplementationGuide}" -gt 0 ] && log "  ImplementationGuide: loaded ${count_ImplementationGuide}"
    rm -rf "${workdir}"
done

log "Done."
