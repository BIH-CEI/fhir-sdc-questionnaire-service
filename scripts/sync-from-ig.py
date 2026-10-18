#!/usr/bin/env python3
"""
ImplementationGuide sync: pull an IG and the conformance/definition resources
it lists in definition.resource[] from a producer FHIR server into a consumer.

Counterpart to sync-from-crmi.py for content that ships as a plain IG package
without a CRMI release manifest — currently PCOR-MII (BIH-CEI). The IG resource
is the contract: the producer loader PUTs ImplementationGuide/<id>, and every
non-example entry in definition.resource[] (Questionnaire, CodeSystem,
ValueSet, ConceptMap, ObservationDefinition, ...) is pulled from the producer
and written to the consumer.

Flow:
  1. Fetch ImplementationGuide/<IG_ID> from producer (retry while the loader runs).
     If the producer never serves it, read the IG from the vendored package
     (IG_PACKAGE) instead — it only supplies the resource LIST; content is
     still pulled from the producer. (PCOR-MII 0.3.0's IG cannot be stored on
     HAPI with auto_create_placeholder_reference_targets: its example Bundle
     references would need placeholder Bundles without a type → HTTP 422.)
  2. For each definition.resource[] entry (examples skipped unless SYNC_EXAMPLES=1):
       a. GET <Type>/<id> from producer; on 404 fall back to canonical search
          ?url=<IG canonical base>/<Type>/<id> (HAPI's package installer may
          store CodeSystem/ValueSet under server-assigned ids).
       b. Write to consumer. If the consumer already holds the same
          url|version (e.g. installed from its own baked-in tarball), update
          that resource in place instead of creating a duplicate canonical.
  3. PUT the ImplementationGuide itself last (warning only if the consumer
     rejects it for the same placeholder reason).

Idempotent. Exit code 0 if every entry synced, non-zero otherwise.

Environment:
  PRODUCER_FHIR_URL   default http://hapi-fhir:8080/fhir
  CONSUMER_FHIR_URL   default http://consumer-hapi:8080/fhir
  IG_ID               default pcor-mii
  SYNC_EXAMPLES       "1" to also sync example resources (they are not loaded
                      on the producer by default, so expect misses)
  WAIT_TIMEOUT        seconds to wait for the servers (default 240)
  IG_WAIT             seconds to wait for the IG to appear on producer (default 90)
  IG_PACKAGE          fallback tgz holding package/ImplementationGuide-<IG_ID>.json
"""

from __future__ import annotations

import json
import os
import sys
import tarfile
import time
from typing import Optional
from urllib.parse import quote

import requests

PRODUCER = os.environ.get("PRODUCER_FHIR_URL", "http://hapi-fhir:8080/fhir").rstrip("/")
CONSUMER = os.environ.get("CONSUMER_FHIR_URL", "http://consumer-hapi:8080/fhir").rstrip("/")
IG_ID = os.environ.get("IG_ID", "pcor-mii")
SYNC_EXAMPLES = os.environ.get("SYNC_EXAMPLES") == "1"
WAIT_TIMEOUT = int(os.environ.get("WAIT_TIMEOUT", "240"))
IG_WAIT = int(os.environ.get("IG_WAIT", "90"))
IG_PACKAGE = os.environ.get("IG_PACKAGE")

JSON_HEADERS = {"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"}


def log(msg: str) -> None:
    print(f"[sync-from-ig] {msg}", flush=True)


def wait_for(base: str, label: str) -> None:
    log(f"Waiting up to {WAIT_TIMEOUT}s for {label} at {base}/metadata ...")
    deadline = time.time() + WAIT_TIMEOUT
    while time.time() < deadline:
        try:
            if requests.get(f"{base}/metadata", timeout=5).ok:
                log(f"{label} is reachable.")
                return
        except requests.RequestException:
            pass
        time.sleep(3)
    raise SystemExit(f"ERROR: {label} not reachable after {WAIT_TIMEOUT}s")


def ig_from_package() -> dict:
    with tarfile.open(IG_PACKAGE) as tf:
        member = tf.extractfile(f"package/ImplementationGuide-{IG_ID}.json")
        if member is None:
            raise SystemExit(f"ERROR: ImplementationGuide-{IG_ID}.json not in {IG_PACKAGE}")
        return json.load(member)


def fetch_ig() -> tuple[dict, bool]:
    """Return (IG, served_by_producer)."""
    # Same race as the CRMI manifest: the producer loader PUTs the IG after
    # boot, so a 404 usually just means "not loaded yet".
    deadline = time.time() + IG_WAIT
    while True:
        r = requests.get(f"{PRODUCER}/ImplementationGuide/{IG_ID}", headers=JSON_HEADERS, timeout=15)
        if r.status_code != 404 or time.time() >= deadline:
            break
        log(f"ImplementationGuide/{IG_ID} not loaded yet (404) — retrying ({int(deadline - time.time())}s left)")
        time.sleep(10)
    if r.ok:
        return r.json(), True
    if r.status_code == 404 and IG_PACKAGE:
        log(f"producer does not serve ImplementationGuide/{IG_ID}; taking the resource list from {IG_PACKAGE}")
        return ig_from_package(), False
    r.raise_for_status()
    raise SystemExit(f"ERROR: ImplementationGuide/{IG_ID} → HTTP {r.status_code}")


def search_one(base: str, rt: str, url: str, version: Optional[str]) -> Optional[dict]:
    params = {"url": url}
    if version:
        params["version"] = version
    r = requests.get(f"{base}/{rt}", params=params, headers=JSON_HEADERS, timeout=15)
    if not r.ok:
        return None
    entries = r.json().get("entry") or []
    if len(entries) > 1:
        log(f"  warning: {len(entries)} matches for {rt}?url={url} on {base}; taking first")
    return entries[0]["resource"] if entries else None


def resolve_on_producer(rt: str, rid: str, canonical_base: str, ig_version: Optional[str]) -> Optional[dict]:
    r = requests.get(f"{PRODUCER}/{rt}/{quote(rid)}", headers=JSON_HEADERS, timeout=15)
    if r.ok:
        return r.json()
    canonical = f"{canonical_base}/{rt}/{rid}"
    res = search_one(PRODUCER, rt, canonical, ig_version) or search_one(PRODUCER, rt, canonical, None)
    if res is None:
        log(f"  read {rt}/{rid} → HTTP {r.status_code}; canonical search {canonical} empty")
    return res


def put_to_consumer(resource: dict) -> tuple[bool, str]:
    rt = resource["resourceType"]
    url, version = resource.get("url"), resource.get("version")
    if url:
        existing = search_one(CONSUMER, rt, url, version)
        if existing and existing.get("id") != resource.get("id"):
            resource = {**resource, "id": existing["id"]}
    rid = resource.get("id")
    if not rid:
        return False, f"missing id on {rt}"
    r = requests.put(f"{CONSUMER}/{rt}/{quote(rid)}", headers=JSON_HEADERS, data=json.dumps(resource), timeout=30)
    if r.status_code in (200, 201):
        return True, f"{rt}/{rid} → HTTP {r.status_code}"
    return False, f"{rt}/{rid} → HTTP {r.status_code} — {r.text[:200]}"


def main() -> int:
    log(f"Producer: {PRODUCER}")
    log(f"Consumer: {CONSUMER}")
    wait_for(PRODUCER, "producer HAPI")
    wait_for(CONSUMER, "consumer HAPI")

    ig, ig_on_producer = fetch_ig()
    ig_url, ig_version = ig.get("url", ""), ig.get("version")
    canonical_base = ig_url.rsplit("/ImplementationGuide/", 1)[0]
    log(f"IG: {ig_url} v{ig_version} ({ig.get('title')})")

    entries = (ig.get("definition") or {}).get("resource") or []
    todo = []
    skipped_examples = 0
    for e in entries:
        ref = (e.get("reference") or {}).get("reference", "")
        if "/" not in ref:
            continue
        if (e.get("exampleBoolean") or e.get("exampleCanonical")) and not SYNC_EXAMPLES:
            skipped_examples += 1
            continue
        todo.append(tuple(ref.split("/", 1)))
    log(f"{len(todo)} resources to sync ({skipped_examples} examples skipped).")

    successes = 0
    failures: list[tuple[str, str]] = []
    for rt, rid in todo:
        resource = resolve_on_producer(rt, rid, canonical_base, ig_version)
        if resource is None:
            failures.append((f"{rt}/{rid}", "not resolved on producer"))
            continue
        ok, detail = put_to_consumer(resource)
        if ok:
            successes += 1
            log(f"  PUT {detail}")
        else:
            failures.append((f"{rt}/{rid}", detail))
            log(f"  PUT failed: {detail}")

    ok, detail = put_to_consumer(ig)
    ig_note = "+ IG" if ok else "IG not stored"
    log(f"→ ImplementationGuide itself: {detail}")
    if not ok and ig_on_producer:
        failures.append((f"ImplementationGuide/{IG_ID}", detail))
    elif not ok:
        # The producer could not store it either — same root cause, not a sync failure.
        log("  warning: IG not stored on consumer (producer does not serve it either) — first lines of the error above")

    log("")
    log(f"Done. Synced {successes}/{len(todo)} resources ({ig_note}).")
    if failures:
        log("Failures:")
        for ref, why in failures:
            log(f"  - {ref} → {why}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
