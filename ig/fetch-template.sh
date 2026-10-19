#!/usr/bin/env bash
# Fetch the BIH IG template (BIH-CEI/bih-fhir-ig-template) at a pinned commit
# into ig/ig-template/. Not vendored: the assets are ~17 MB (plantuml.jar etc.).
# Bump TEMPLATE_REF deliberately to pick up template changes.
set -euo pipefail
TEMPLATE_REF=3aa9a7e5263fd80c8c987c24c996378de8bc2699   # 2026-03-18
DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$DIR/ig-template/.ref" ] && [ "$(cat "$DIR/ig-template/.ref")" = "$TEMPLATE_REF" ] && exit 0
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
git -C "$tmp" init -q
git -C "$tmp" fetch -q --depth 1 https://github.com/BIH-CEI/bih-fhir-ig-template.git "$TEMPLATE_REF"
git -C "$tmp" checkout -q FETCH_HEAD
rm -rf "$DIR/ig-template"
cp -R "$tmp/bih-fhir-ig-template/assets/ig-template" "$DIR/ig-template"
# Template bug (as of 3aa9a7e5): the header references the logos without
# their assets/images/ path, so every page gets two broken image links.
sed -i.bak -E 's#src="(Logo_Charite|BIH-Logo_neu)\.png"#src="assets/images/\1.png"#' \
    "$DIR/ig-template/includes/fragment-header.html"
rm -f "$DIR/ig-template/includes/fragment-header.html.bak"
echo "$TEMPLATE_REF" > "$DIR/ig-template/.ref"
echo "BIH IG template ${TEMPLATE_REF:0:8} -> ig/ig-template"
