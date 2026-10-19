"""PCOR-MII content and runtime terminology — formerly bash in build-and-publish.yml.

- PCOR-MII Questionnaires resolvable by url+version (incl. the metadata-only UKHD-EDP)
- PCOR-MII terminology installed at all: it ships status=draft and only lands
  thanks to the draft→active patch in Dockerfile.form-manager
- ValueSet/$expand works at runtime (needs Hibernate Search / Lucene; the
  packages ship no expansions)

$expand is polled: right after boot (and after every package install) HAPI
deletes and re-stores its TermValueSets and queues PRE_EXPAND_VALUESET jobs.
While a ValueSet's pre-expansion is in flight, $expand answers 200 with an
empty expansion. The publish workflow runs these tests seconds after boot,
so a single request cannot tell "not yet" from "broken".
"""
import asyncio
import time

import pytest

from tests.conftest import PCOR_MII_VERSION

pytestmark = [pytest.mark.content, pytest.mark.asyncio]

PCOR_BASE = "https://bih-cei.github.io/PCOR-MII"
EXPAND_TIMEOUT_S = 90


async def _expand(fhir_server, url: str, min_codes: int) -> dict:
    """$expand `url`, polling until the expansion has at least `min_codes`
    entries or EXPAND_TIMEOUT_S is up. Returns the last expansion either way,
    so the caller's assertion reports what HAPI finally answered."""
    deadline = time.monotonic() + EXPAND_TIMEOUT_S
    while True:
        r = await fhir_server.get("/ValueSet/$expand", params={"url": url})
        assert r.status_code == 200, r.text[:300]
        expansion = r.json().get("expansion", {})
        if len(expansion.get("contains", [])) >= min_codes or time.monotonic() > deadline:
            return expansion
        await asyncio.sleep(2)


async def test_pcor_questionnaire_resolvable_by_url_and_version(fhir_server):
    r = await fhir_server.get(
        "/Questionnaire",
        params={"url": f"{PCOR_BASE}/Questionnaire/UKHDEDP", "version": PCOR_MII_VERSION, "_summary": "count"},
    )
    assert r.json().get("total", 0) == 1, f"PCOR-MII {PCOR_MII_VERSION} UKHDEDP not loaded"


async def test_pcor_questionnaires_present_in_bulk(fhir_server):
    r = await fhir_server.get("/Questionnaire", params={"url:below": f"{PCOR_BASE}/Questionnaire/", "_summary": "count"})
    assert r.json().get("total", 0) >= 20, "fewer than 20 PCOR-MII Questionnaires loaded"


async def test_pcor_terminology_installed_despite_draft_status(fhir_server):
    r = await fhir_server.get(
        "/CodeSystem", params={"url": f"{PCOR_BASE}/CodeSystem/pcor-item-dictionary", "_summary": "count"},
    )
    assert r.json().get("total", 0) == 1, (
        "pcor-item-dictionary missing — draft→active patch in Dockerfile.form-manager "
        "not applied or HAPI skipped it"
    )


async def test_valueset_expand_works_at_runtime(fhir_server):
    expansion = await _expand(fhir_server, f"{PCOR_BASE}/ValueSet/ukhd-edp-stufe-6-vs", min_codes=1)
    assert len(expansion.get("contains", [])) >= 1, (
        f"ValueSet/$expand returned no codes after {EXPAND_TIMEOUT_S}s — "
        "Hibernate Search / Lucene not initialised?"
    )


async def test_mii_pro_valueset_expand_works(fhir_server):
    """The answerValueSets clients will actually expand."""
    url = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
    expansion = await _expand(fhir_server, url, min_codes=4)
    codes = [c.get("code") for c in expansion.get("contains", [])]
    assert len(codes) == 4, f"expected the 4 scale codes after {EXPAND_TIMEOUT_S}s, got {codes}"
