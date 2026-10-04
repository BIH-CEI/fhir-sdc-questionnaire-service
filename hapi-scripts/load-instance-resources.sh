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
LOAD_TYPES=(Questionnaire Library Provenance ImplementationGuide ObservationDefinition TestScript)

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
# VERSIONS-RETENTION, PRAEZISIERT: Nur die NEUESTE Version je Package behaelt
# die Package-id (PUT /<Typ>/<id>) — Konsumenten und Tests duerfen sich auf
# id-Stabilitaet des aktuellen Standes verlassen. AELTERE Versionen werden
# per Conditional Update auf (url, version) ohne Body-id angelegt: als
# eigene, per ?url=&version= aufloesbare Ressourcen, ohne die aktuelle zu
# ueberschreiben und ohne id-Kollision.
latest_for() {  # $1 = package name -> hoechste Version im PKGS_DIR
    local name="$1" best=""
    for t in "${PKGS_DIR}"/*.tgz; do
        local pj n v
        pj=$(tar xzf "$t" -O --wildcards "*package/package.json" 2>/dev/null) || continue
        n=$(printf '%s' "$pj" | jq -r '.name // empty')
        v=$(printf '%s' "$pj" | jq -r '.version // empty')
        [ "$n" = "$name" ] || continue
        if [ -z "$best" ] || [ "$(printf '%s\n%s\n' "$best" "$v" | sort -V | tail -1)" = "$v" ]; then
            best="$v"
        fi
    done
    printf '%s' "$best"
}

for tarball in "${PKGS_DIR}"/*.tgz; do
    pkg_name=$(basename "${tarball}" .tgz)
    workdir="/tmp/load-${pkg_name}"
    rm -rf "${workdir}" && mkdir -p "${workdir}"
    tar xzf "${tarball}" -C "${workdir}"

    pkg_json=$(tar xzf "${tarball}" -O --wildcards "*package/package.json" 2>/dev/null || true)
    this_name=$(printf '%s' "$pkg_json" | jq -r '.name // empty')
    this_ver=$(printf '%s' "$pkg_json" | jq -r '.version // empty')
    is_latest=0
    if [ -z "$this_name" ]; then
        # package.json nicht lesbar -> fail-open: wie bisher per id laden,
        # statt das Paket stillschweigend zu ueberspringen.
        is_latest=1
    elif [ "$this_ver" = "$(latest_for "$this_name")" ]; then
        is_latest=1
    fi
    # RETENTION IST OPT-IN (RETAIN_PRIOR_VERSIONS=1): Aeltere Tarballs tragen
    # Questionnaires, deren Terminologie (VS/CS) NICHT installiert wird — bei
    # unversionierter Canonical-Aufloesung kann HAPI CR dann eine alte Version
    # mit nicht aufloesbaren ValueSet-Referenzen erwischen ($package leer,
    # $compute 422). Default ist deshalb deterministisch: nur latest. Fuer
    # Audit-/Altdaten-Szenarien RETAIN_PRIOR_VERSIONS=1 setzen — dann landen
    # Vorversionen als eigene, per ?url=&version= aufloesbare Ressourcen
    # (Conditional Update, ohne Body-id) zusaetzlich auf dem Server.
    if [ "${is_latest}" -eq 0 ] && [ "${RETAIN_PRIOR_VERSIONS:-0}" != "1" ]; then
        log "--- ${pkg_name} (latest=0) uebersprungen — RETAIN_PRIOR_VERSIONS!=1 ---"
        continue
    fi
    log "--- ${pkg_name} (latest=$is_latest) ---"
    # Per-type counters — flat variables for bash 3.x portability (macOS)
    count_Questionnaire=0
    count_Library=0
    count_Provenance=0
    count_ImplementationGuide=0
    count_ObservationDefinition=0
    count_TestScript=0

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

        # VERSION RETENTION (audit): canonical resources are upserted by
        # (url, version) via conditional update — a new business version
        # CREATES a new server resource instead of clobbering the previous
        # one under the same id. Same-version re-runs stay idempotent
        # updates. Earlier versions therefore remain resolvable as current
        # resources via ?url=...&version=... — required for audit and for
        # QuestionnaireResponses that pin |<old-version>.
        # Resources without url/version (e.g. Provenance) keep the id-PUT.
        curl_url=$(jq -r '.url // empty' "${jsonfile}")
        curl_ver=$(jq -r '.version // empty' "${jsonfile}")
        if [ "${is_latest}" -eq 0 ] && [ -n "${curl_url}" ] && [ -n "${curl_ver}" ]; then
            # Body-id entfernen: Beim Conditional-Create wuerde die mit der
            # id der Vorversion kollidieren (409). Server vergibt die id;
            # Aufloesung laeuft ueber url|version, nicht ueber die id.
            jq 'del(.id)' "${jsonfile}" > "${jsonfile}.noid"
            http_code=$(curl -s -o /dev/null -w "%{http_code}" \
                -X PUT "${HAPI_URL}/${rt}?url=${curl_url}&version=${curl_ver}" \
                -H "Content-Type: application/fhir+json" \
                --data-binary @"${jsonfile}.noid")
            rm -f "${jsonfile}.noid"
        else
            http_code=$(curl -s -o /dev/null -w "%{http_code}" \
                -X PUT "${HAPI_URL}/${rt}/${rid}" \
                -H "Content-Type: application/fhir+json" \
                --data-binary @"${jsonfile}")
        fi

        if [[ "${http_code}" =~ ^2 ]]; then
            case "${rt}" in
                Questionnaire)        count_Questionnaire=$((count_Questionnaire + 1)) ;;
                Library)              count_Library=$((count_Library + 1)) ;;
                Provenance)           count_Provenance=$((count_Provenance + 1)) ;;
                ImplementationGuide)  count_ImplementationGuide=$((count_ImplementationGuide + 1)) ;;
                ObservationDefinition) count_ObservationDefinition=$((count_ObservationDefinition + 1)) ;;
                TestScript)           count_TestScript=$((count_TestScript + 1)) ;;
            esac
        else
            log "  WARN: PUT ${rt}/${rid} returned HTTP ${http_code}"
        fi
    done

    [ "${count_Questionnaire}" -gt 0 ]       && log "  Questionnaire: loaded ${count_Questionnaire}"
    [ "${count_Library}" -gt 0 ]             && log "  Library: loaded ${count_Library}"
    [ "${count_Provenance}" -gt 0 ]          && log "  Provenance: loaded ${count_Provenance}"
    [ "${count_ImplementationGuide}" -gt 0 ] && log "  ImplementationGuide: loaded ${count_ImplementationGuide}"
    [ "${count_ObservationDefinition}" -gt 0 ] && log "  ObservationDefinition: loaded ${count_ObservationDefinition}"
    [ "${count_TestScript}" -gt 0 ]          && log "  TestScript: loaded ${count_TestScript}"
    rm -rf "${workdir}"
done

log "Done."
