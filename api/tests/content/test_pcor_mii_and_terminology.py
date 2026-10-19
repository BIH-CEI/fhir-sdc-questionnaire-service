"""PCOR-MII content and runtime terminology — formerly bash in build-and-publish.yml.

- PCOR-MII Questionnaires resolvable by url+version (incl. the metadata-only UKHD-EDP)
- PCOR-MII terminology installed at all: it ships status=draft and only lands
  thanks to the draft→active patch in Dockerfile.form-manager
- ValueSet/$expand works at runtime (needs Hibernate Search / Lucene; the
  packages ship no expansions)
"""
import pytest

from tests.conftest import PCOR_MII_VERSION

pytestmark = [pytest.mark.content, pytest.mark.asyncio]

PCOR_BASE = "https://bih-cei.github.io/PCOR-MII"


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
    r = await fhir_server.get("/ValueSet/$expand", params={"url": f"{PCOR_BASE}/ValueSet/ukhd-edp-stufe-6-vs"})
    assert r.status_code == 200, r.text[:300]
    expansion = r.json().get("expansion", {})
    assert expansion.get("total", len(expansion.get("contains", []))) >= 1, (
        "ValueSet/$expand returned no codes — Hibernate Search / Lucene not initialised?"
    )


async def test_mii_pro_valueset_expand_works(fhir_server):
    """The answerValueSets clients will actually expand."""
    url = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
    r = await fhir_server.get("/ValueSet/$expand", params={"url": url})
    assert r.status_code == 200, r.text[:300]
    assert len(r.json().get("expansion", {}).get("contains", [])) == 4
