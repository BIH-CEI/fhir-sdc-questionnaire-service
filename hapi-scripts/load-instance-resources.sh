#!/bin/bash
# Post-startup loader: PUT the resource types HAPI's PackageInstallerSvc
# skips on auto-install (Questionnaire, Library, Provenance, ImplementationGuide,
# ObservationDefinition, TestScript).
#
# HAPI's PackageInstallerSvcImpl only handles NamingSystem, CodeSystem,
# ValueSet, StructureDefinition, ConceptMap, SearchParameter, Subscription.
# Anything else in an installed FHIR Package is silently ignored — so the
# pro-library PHQ-9, the release manifest Library, and the Provenance never
# land in HAPI unless we PUT them ourselves after the server is reachable.
#
# This script:
#   1. Waits for HAPI metadata endpoint
#   2. For each tarball in $PKGS_DIR/*.tgz:
#      - extracts it
#      - for each .json of a LOAD_TYPES resource: PUT it (see VERSION RETENTION)
#   3. Logs per-package per-type counts
#
# VERSION RETENTION
#   Several versions of one package may sit in $PKGS_DIR. The NEWEST version
#   (proper ordering: a pre-release such as 2027.0.0-ballot.1 ranks BELOW
#   2027.0.0) is loaded by id, so consumers and tests can rely on the package
#   ids of the current content. Older versions are loaded only when they are
#   declared in RETAINED_PACKAGE_VERSIONS (space-separated "<name>@<version>",
#   e.g. "de.medizininformatikinitiative.kerndatensatz.pros@2026.7.0"); the
#   image sets this from its MII_PRO_RETAINED_VERSIONS build-arg, which is
#   also what installs that version's profiles and terminology. Undeclared
#   older tarballs are skipped: their ValueSets would not be on the server and
#   their Questionnaires would resolve against the newest terminology.
#   Retained resources are created by conditional update on (url, version)
#   with the body id stripped, so they never clobber the current ids and stay
#   resolvable via ?url=…&version=…. Resources without url+version
#   (ObservationDefinition in R4, Provenance) cannot be versioned that way and
#   are NOT loaded for retained versions — the current version's copy wins.

set -euo pipefail

HAPI_URL="${HAPI_URL:-http://localhost:8080/fhir}"
PKGS_DIR="${PKGS_DIR:-/data/hapi/local-packages}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-180}"
RETAINED_PACKAGE_VERSIONS="${RETAINED_PACKAGE_VERSIONS:-}"
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

# Sortable key for a version string: zero-padded numeric parts, then a
# release flag (1) or pre-release flag (0) so "2027.0.0" > "2027.0.0-ballot.1",
# then the pre-release label for ordering among pre-releases.
ver_key() {  # $1 = version
    awk -F'-' '{
        n = split($1, p, ".");
        rel = ($2 == "") ? 1 : 0;
        printf "%06d.%06d.%06d.%d.%s", p[1]+0, p[2]+0, p[3]+0, rel, $2
    }' <<<"$1"
}

pkg_meta() {  # $1 = tarball -> "name version" (empty if unreadable)
    # Portable across GNU tar and bsdtar (macOS has no --wildcards): tarballs
    # carry package.json as "package/package.json" or "./package/package.json".
    local pj
    pj=$(tar xzf "$1" -O package/package.json 2>/dev/null) \
        || pj=$(tar xzf "$1" -O ./package/package.json 2>/dev/null) \
        || { echo ""; return; }
    printf '%s %s' "$(jq -r '.name // empty' <<<"$pj")" "$(jq -r '.version // empty' <<<"$pj")"
}

latest_for() {  # $1 = package name -> newest version among tarballs in PKGS_DIR
    local name="$1" best="" best_key="" t n v k
    for t in "${PKGS_DIR}"/*.tgz; do
        read -r n v <<<"$(pkg_meta "$t")"
        [ "$n" = "$name" ] || continue
        k=$(ver_key "$v")
        if [ -z "$best" ] || [[ "$k" > "$best_key" ]]; then
            best="$v"; best_key="$k"
        fi
    done
    printf '%s' "$best"
}

is_retained() {  # $1 = name, $2 = version
    local entry
    for entry in ${RETAINED_PACKAGE_VERSIONS}; do
        [ "$entry" = "$1@$2" ] && return 0
    done
    return 1
}

shopt -s nullglob
for tarball in "${PKGS_DIR}"/*.tgz; do
    pkg_name=$(basename "${tarball}" .tgz)
    workdir="/tmp/load-${pkg_name}"
    rm -rf "${workdir}" && mkdir -p "${workdir}"
    tar xzf "${tarball}" -C "${workdir}"

    read -r this_name this_ver <<<"$(pkg_meta "$tarball")"
    is_latest=0
    if [ -z "${this_name}" ]; then
        # package.json unreadable → fail open: load by id rather than
        # silently skipping the package — but say so, because an older
        # version loaded by id overwrites the current one.
        log "WARN: ${pkg_name}: package.json unreadable, treating as latest (loaded by id)"
        is_latest=1
    elif [ "$this_ver" = "$(latest_for "$this_name")" ]; then
        is_latest=1
    fi
    if [ "${is_latest}" -eq 0 ] && ! is_retained "$this_name" "$this_ver"; then
        log "--- ${pkg_name}: older version, not in RETAINED_PACKAGE_VERSIONS — skipped ---"
        rm -rf "${workdir}"
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
    skipped_unversioned=0

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

        curl_url=$(jq -r '.url // empty' "${jsonfile}")
        curl_ver=$(jq -r '.version // empty' "${jsonfile}")
        if [ "${is_latest}" -eq 0 ]; then
            if [ -z "${curl_url}" ] || [ -z "${curl_ver}" ]; then
                # Cannot be distinguished from the current version's copy
                # (no canonical|version) — do not overwrite the current id.
                skipped_unversioned=$((skipped_unversioned + 1))
                continue
            fi
            # Strip body id: a conditional create would collide with the
            # current version's id (409). The server assigns the id;
            # resolution runs via url|version, not via id.
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
    [ "${skipped_unversioned}" -gt 0 ]       && log "  retained version: ${skipped_unversioned} resources without url|version not loaded (current version's copy kept)"
    rm -rf "${workdir}"
done

log "Done."
