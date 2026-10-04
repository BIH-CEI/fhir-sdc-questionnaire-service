#!/usr/bin/env python3
"""
CRMI manifest sync: pull a release Library and all its relatedArtifact[]
from a producer FHIR server into a consumer FHIR server.

The "manifest" is a CRMI Library of type=asset-collection, e.g.
  https://fhir.bih-charite.de/pro-library/Library/release-0-1-3
listing every artefact (Questionnaire, Library, TestScript, ObservationDefinition,
...) with their pinned versions in relatedArtifact[].resource as a canonical URL
(possibly suffixed `|version`).

Flow:
  1. Fetch the manifest from producer (by ID or canonical URL).
  2. For each relatedArtifact[].resource:
       a. Split into (canonical_url, version?).
       b. Infer resourceType from the URL path segment before the last `/`.
       c. Search producer: `GET /<rt>?url=<canonical>[&version=<v>]`.
       d. Take the first matching resource.
       e. PUT it into the consumer keeping the original id.
  3. PUT the manifest Library itself last so consumers can also serve it.

Idempotent: re-running overwrites existing resources (PUT by id).
Exit code: 0 if every artefact synced; non-zero if any failed.

Environment:
  PRODUCER_FHIR_URL   default http://hapi-fhir:8080/fhir
  CONSUMER_FHIR_URL   default http://consumer-hapi:8080/fhir
  MANIFEST_ID         e.g. release-0-1-3 (resolved against PRODUCER_FHIR_URL)
  MANIFEST_URL        full canonical, overrides MANIFEST_ID lookup
  WAIT_TIMEOUT        seconds to wait for producer to come up (default 240)
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, urlparse

import requests

PRODUCER = os.environ.get("PRODUCER_FHIR_URL", "http://hapi-fhir:8080/fhir").rstrip("/")
CONSUMER = os.environ.get("CONSUMER_FHIR_URL", "http://consumer-hapi:8080/fhir").rstrip("/")
MANIFEST_ID = os.environ.get("MANIFEST_ID", "release-0-1-3")
MANIFEST_URL = os.environ.get("MANIFEST_URL")
WAIT_TIMEOUT = int(os.environ.get("WAIT_TIMEOUT", "240"))

JSON_HEADERS = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}


def log(msg: str) -> None:
    print(f"[sync-from-crmi] {msg}", flush=True)


def wait_for(base: str, label: str) -> None:
    log(f"Waiting up to {WAIT_TIMEOUT}s for {label} at {base}/metadata ...")
    deadline = time.time() + WAIT_TIMEOUT
    while time.time() < deadline:
        try:
            r = requests.get(f"{base}/metadata", timeout=5)
            if r.ok:
                log(f"{label} is reachable.")
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise SystemExit(f"ERROR: {label} not reachable after {WAIT_TIMEOUT}s")


def fetch_manifest() -> dict:
    if MANIFEST_URL:
        log(f"Resolving manifest by canonical URL: {MANIFEST_URL}")
        # Strip optional |version suffix the same way relatedArtifact entries do.
        canonical, _, version = MANIFEST_URL.partition("|")
        params = {"url": canonical}
        if version:
            params["version"] = version
        r = requests.get(f"{PRODUCER}/Library", params=params, headers=JSON_HEADERS, timeout=15)
        r.raise_for_status()
        bundle = r.json()
        entries = bundle.get("entry") or []
        if not entries:
            raise SystemExit(f"ERROR: manifest not found by canonical URL {MANIFEST_URL}")
        return entries[0]["resource"]
    log(f"Fetching manifest Library/{MANIFEST_ID} from producer.")
    r = requests.get(f"{PRODUCER}/Library/{MANIFEST_ID}", headers=JSON_HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


@dataclass
class ArtefactRef:
    canonical: str
    version: Optional[str]
    display: Optional[str]

    @property
    def resource_type(self) -> Optional[str]:
        # Canonical URL convention: .../<ResourceType>/<id>
        try:
            path = urlparse(self.canonical).path.rstrip("/")
            seg = path.split("/")
            # Expect at least .../<ResourceType>/<id>
            if len(seg) >= 2:
                return seg[-2]
        except Exception:
            pass
        return None

    @property
    def id_hint(self) -> Optional[str]:
        """Last path segment of the canonical URL — usable as a fallback
        when the producer doesn't index a `url` SearchParameter for this
        resource type (e.g. ObservationDefinition in HAPI by default)."""
        try:
            path = urlparse(self.canonical).path.rstrip("/")
            seg = path.split("/")
            if seg:
                return seg[-1]
        except Exception:
            pass
        return None


def parse_related(library: dict) -> list[ArtefactRef]:
    out: list[ArtefactRef] = []
    for ra in library.get("relatedArtifact", []) or []:
        if ra.get("type") not in {"depends-on", "composed-of"}:
            # CRMI asset-collection uses depends-on; tolerate composed-of too.
            continue
        ref = ra.get("resource")
        if not ref:
            continue
        canonical, _, version = ref.partition("|")
        out.append(ArtefactRef(canonical=canonical, version=version or None, display=ra.get("display")))
    return out


def resolve_artefact(ref: ArtefactRef) -> Optional[dict]:
    """Try canonical-URL search first (the CRMI-correct way). Fall back to
    GET by id derived from the canonical URL's last segment, since some
    resource types (notably ObservationDefinition in stock HAPI) don't have
    a `url` SearchParameter registered."""
    rt = ref.resource_type
    if not rt:
        log(f"  skip: cannot infer resourceType from {ref.canonical}")
        return None

    params = {"url": ref.canonical}
    if ref.version:
        params["version"] = ref.version
    r = requests.get(f"{PRODUCER}/{rt}", params=params, headers=JSON_HEADERS, timeout=15)
    if r.ok:
        entries = (r.json().get("entry") or [])
        if entries:
            if len(entries) > 1:
                log(f"  warning: {len(entries)} matches for {rt} {ref.canonical}; taking first")
            return entries[0]["resource"]
        log(f"  canonical search empty for {rt} {ref.canonical}; trying read-by-id fallback")
    else:
        log(f"  canonical search {rt}?url=… → HTTP {r.status_code}; trying read-by-id fallback")

    # Fallback: GET /<rt>/<id>. Resource ids in our pro-library happen to
    # match the last canonical path segment (e.g. cei-obsdef-phq-9-score).
    rid = ref.id_hint
    if not rid:
        return None
    r2 = requests.get(f"{PRODUCER}/{rt}/{rid}", headers=JSON_HEADERS, timeout=15)
    if not r2.ok:
        log(f"  read fallback {rt}/{rid} → HTTP {r2.status_code}")
        return None
    res = r2.json()
    # Verify the canonical URL matches what the manifest claimed, to avoid
    # silently pulling a same-id resource that's actually a different thing.
    if res.get("url") and res["url"] != ref.canonical:
        log(f"  warning: read-by-id {rt}/{rid} has url={res['url']} (manifest said {ref.canonical})")
    return res


def put_to_consumer(resource: dict) -> tuple[bool, str]:
    rt = resource.get("resourceType")
    rid = resource.get("id")
    if not rt or not rid:
        return False, f"missing resourceType/id: {rt}/{rid}"
    r = requests.put(
        f"{CONSUMER}/{rt}/{quote(rid)}",
        headers=JSON_HEADERS,
        data=json.dumps(resource),
        timeout=30,
    )
    if r.status_code in (200, 201):
        return True, f"HTTP {r.status_code}"
    return False, f"HTTP {r.status_code} — {r.text[:200]}"


def main() -> int:
    log(f"Producer: {PRODUCER}")
    log(f"Consumer: {CONSUMER}")
    wait_for(PRODUCER, "producer HAPI")
    wait_for(CONSUMER, "consumer HAPI")

    manifest = fetch_manifest()
    log(f"Manifest: {manifest.get('url')} v{manifest.get('version')} ({manifest.get('title')})")
    refs = parse_related(manifest)
    log(f"Found {len(refs)} relatedArtifact entries to sync.")

    successes = 0
    failures: list[tuple[ArtefactRef, str]] = []

    for ref in refs:
        label = f"{ref.resource_type or '??'} {ref.canonical}" + (f"|{ref.version}" if ref.version else "")
        log(f"→ {label}")
        resource = resolve_artefact(ref)
        if resource is None:
            failures.append((ref, "not resolved on producer"))
            continue
        ok, detail = put_to_consumer(resource)
        if ok:
            successes += 1
            log(f"  PUT {resource['resourceType']}/{resource.get('id')} → {detail}")
        else:
            failures.append((ref, detail))
            log(f"  PUT failed: {detail}")

    # PUT the manifest itself last — gives the consumer the same manifest the
    # producer published, so downstream consumers can chain off the consumer too.
    log(f"→ Manifest itself: Library/{manifest.get('id')}")
    ok, detail = put_to_consumer(manifest)
    if ok:
        log(f"  PUT Library/{manifest.get('id')} → {detail}")
    else:
        failures.append((ArtefactRef(canonical=manifest.get("url", ""), version=manifest.get("version"), display="manifest"), detail))
        log(f"  PUT manifest failed: {detail}")

    log("")
    log(f"Done. Synced {successes}/{len(refs)} artefacts (+ manifest).")
    if failures:
        log("Failures:")
        for ref, why in failures:
            log(f"  - {ref.resource_type or '??'} {ref.canonical}|{ref.version or ''} → {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
