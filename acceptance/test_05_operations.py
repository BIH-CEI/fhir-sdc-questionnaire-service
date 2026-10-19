"""5 Operations: terminology, CRMI $package, localization, error shape."""
import os
import time

import pytest

from conftest import EXPECT_MII_PRO, FHIR_JSON, MII_PRO_BASE, outcome_code

pytestmark = pytest.mark.operations

MII_PHQ9 = f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-phq-9"
VS_4PT = f"{MII_PRO_BASE}/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
CRMI_MANIFEST = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-manifestlibrary"


@pytest.fixture(scope="module")
def phq9_id(base, client):
    params = {"url": MII_PHQ9, "_elements": "id"}
    if EXPECT_MII_PRO:
        params["version"] = EXPECT_MII_PRO
    entries = client.get(f"{base}/Questionnaire", params=params).json().get("entry", [])
    assert entries, "MII PRO PHQ-9 not found"
    return entries[0]["resource"]["id"]


def test_valueset_expand_get(base, client):
    """Right after a fresh start HAPI pre-expands ValueSets for a while;
    expansions can be empty in that window, so poll before failing."""
    deadline = time.monotonic() + float(os.getenv("FM_EXPAND_SETTLE", "90"))
    while True:
        r = client.get(f"{base}/ValueSet/$expand", params={"url": VS_4PT})
        assert r.status_code == 200, r.text[:200]
        codes = r.json().get("expansion", {}).get("contains", [])
        if len(codes) == 4 or time.monotonic() > deadline:
            break
        time.sleep(3)
    assert len(codes) == 4, f"expected 4 codes, got {len(codes)}"


def test_valueset_expand_post(base, client):
    body = {"resourceType": "Parameters", "parameter": [{"name": "url", "valueUri": VS_4PT}]}
    r = client.post(f"{base}/ValueSet/$expand", json=body, headers={"Content-Type": FHIR_JSON})
    assert r.status_code == 200, r.text[:200]
    assert r.json()["resourceType"] == "ValueSet"


def test_package_is_crmi_with_outcome_manifest_first(base, client, phq9_id):
    r = client.get(f"{base}/Questionnaire/{phq9_id}/$package")
    assert r.status_code == 200, r.text[:300]
    bundle = r.json()
    assert bundle["resourceType"] == "Bundle" and bundle["type"] == "collection"
    manifest = bundle["entry"][0]["resource"]
    assert manifest["resourceType"] == "Library"
    assert CRMI_MANIFEST in manifest["meta"]["profile"]
    assert bundle["entry"][1]["resource"]["url"] == MII_PHQ9
    depends_on = {ra["resource"] for ra in manifest.get("relatedArtifact", []) if ra["type"] == "depends-on"}
    packaged = {f"{e['resource']['url']}|{e['resource'].get('version')}" for e in bundle["entry"][2:]}
    assert packaged <= depends_on, f"packaged but not in the manifest: {packaged - depends_on}"


def test_package_by_canonical(base, client):
    params = {"url": MII_PHQ9}
    if EXPECT_MII_PRO:
        params["version"] = EXPECT_MII_PRO
    r = client.get(f"{base}/Questionnaire/$package", params=params)
    assert r.status_code == 200, r.text[:300]
    q = r.json()["entry"][1]["resource"]
    assert q["url"] == MII_PHQ9
    if EXPECT_MII_PRO:
        assert q["version"] == EXPECT_MII_PRO


def test_languages_and_localize(base, client, phq9_id):
    r = client.get(f"{base}/Questionnaire/{phq9_id}/$languages")
    assert r.status_code == 200, r.text[:200]
    langs = [p.get("valueCode") for p in r.json().get("parameter", [])]
    assert "de" in langs, langs
    r = client.get(f"{base}/Questionnaire/{phq9_id}/$localize", params={"language": "de"})
    assert r.status_code == 200, r.text[:200]
    assert r.json()["resourceType"] == "Questionnaire"


def test_unknown_resource_is_an_operation_outcome(base, client):
    r = client.get(f"{base}/Questionnaire/acceptance-probe-does-not-exist")
    assert r.status_code in (404, 410)
    assert outcome_code(r) in ("not-found", "processing", "deleted")


def test_unknown_package_is_an_operation_outcome(base, client):
    r = client.get(f"{base}/Questionnaire/acceptance-probe-does-not-exist/$package")
    assert r.status_code == 404, r.text[:200]
    assert outcome_code(r) == "not-found"
