"""MII PRO content: current version plus retained versions (Option A).

The image installs the profiles and terminology of MII_PRO_VERSION and of
every version in MII_PRO_RETAINED_VERSIONS (Dockerfile.form-manager), and the
post-boot loader adds their Questionnaires. This suite proves:

- every version is resolvable by canonical|version for each resource type,
- the current version keeps the package ids, retained ones do not clobber them,
- an unversioned lookup picks the current version (release > pre-release,
  not "last written"),
- packaging an older Questionnaire resolves its unversioned ValueSet
  references to that version's own terminology, not the newest.

Only `fhir_server` (HAPI) and the in-process sidecar are needed.
"""
import pytest

from tests.conftest import (
    MII_PRO_BASE,
    MII_PRO_RETAINED_VERSIONS,
    MII_PRO_VERSION,
)

pytestmark = [pytest.mark.content, pytest.mark.asyncio]

ALL_VERSIONS = [MII_PRO_VERSION, *MII_PRO_RETAINED_VERSIONS]

PHQ9_URL = f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-phq-9"
QLQ_C30_URL = f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-eortc-qlq-c30"
SCALE_4PT_VS = f"{MII_PRO_BASE}/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
QLQ_C30_CS = f"{MII_PRO_BASE}/CodeSystem/mii-cs-pro-eortc-qlq-c30"
QR_PROFILE = f"{MII_PRO_BASE}/StructureDefinition/mii-pr-pro-questionnaire-response"


async def _count(fhir_server, rtype: str, url: str, version: str | None = None) -> int:
    params = {"url": url, "_summary": "count"}
    if version:
        params["version"] = version
    r = await fhir_server.get(f"/{rtype}", params=params)
    r.raise_for_status()
    return r.json().get("total", 0)


@pytest.mark.parametrize("version", ALL_VERSIONS)
@pytest.mark.parametrize("rtype,url", [
    ("Questionnaire", PHQ9_URL),
    ("ValueSet", SCALE_4PT_VS),
    ("CodeSystem", QLQ_C30_CS),
    ("StructureDefinition", QR_PROFILE),
])
async def test_each_version_resolvable_by_canonical_and_version(fhir_server, rtype, url, version):
    assert await _count(fhir_server, rtype, url, version) == 1, (
        f"{rtype} {url}|{version} not on the server — installer/loader did not "
        f"load MII PRO {version}"
    )


async def test_one_resource_per_canonical_and_version(fhir_server):
    """No duplicates: exactly len(ALL_VERSIONS) PHQ-9 Questionnaires, one per version."""
    r = await fhir_server.get("/Questionnaire", params={"url": PHQ9_URL, "_elements": "version"})
    versions = sorted(e["resource"].get("version") for e in r.json().get("entry", []))
    assert versions == sorted(ALL_VERSIONS)


async def test_current_version_keeps_package_id(fhir_server):
    r = await fhir_server.get("/Questionnaire/mii-qst-pro-phq-9")
    assert r.status_code == 200
    assert r.json()["version"] == MII_PRO_VERSION


async def test_current_version_has_profiles_installed(fhir_server):
    r = await fhir_server.get("/StructureDefinition", params={"version": MII_PRO_VERSION, "_summary": "count"})
    assert r.json().get("total", 0) >= 20, "MII PRO StructureDefinitions missing at the current version"


async def test_unversioned_package_lookup_picks_current_version(api_client):
    r = await api_client.get("/api/questionnaires/$package", params={"url": PHQ9_URL, "include-dependencies": False})
    assert r.status_code == 200
    # entry[0] is the CRMI outcome manifest, entry[1] the Questionnaire
    assert r.json()["entry"][1]["resource"]["version"] == MII_PRO_VERSION


def _external_valueset_refs(q: dict) -> set:
    refs = set()

    def walk(items):
        for item in items:
            ref = item.get("answerValueSet")
            if ref and not ref.startswith("#"):
                refs.add(ref)
            walk(item.get("item", []))

    walk(q.get("item", []))
    return refs


@pytest.mark.skipif(not MII_PRO_RETAINED_VERSIONS, reason="no retained MII PRO versions configured")
async def test_retained_questionnaire_packages_with_its_own_terminology(fhir_server, api_client):
    """$package of an older Questionnaire must carry that version's ValueSets
    and CodeSystems, although it references them without |version."""
    old = MII_PRO_RETAINED_VERSIONS[0]
    r = await fhir_server.get("/Questionnaire", params={"version": old, "url:below": MII_PRO_BASE, "_count": 100})
    r.raise_for_status()
    candidates = [e["resource"] for e in r.json().get("entry", []) if _external_valueset_refs(e["resource"])]
    assert candidates, f"no MII PRO {old} Questionnaire with external answerValueSet bindings on the server"
    q_old = candidates[0]

    r = await api_client.get("/api/questionnaires/$package", params={"url": q_old["url"], "version": old})
    assert r.status_code == 200, r.text[:300]
    entries = r.json()["entry"]
    manifest, questionnaire = entries[0]["resource"], entries[1]["resource"]
    assert questionnaire["version"] == old
    assert "contained" not in manifest, manifest.get("contained")  # no packaging messages

    by_type = {}
    for e in entries[2:]:
        res = e["resource"]
        by_type.setdefault(res["resourceType"], []).append(res)
    assert {vs["url"] for vs in by_type["ValueSet"]} >= _external_valueset_refs(q_old)
    assert {vs["version"] for vs in by_type["ValueSet"]} == {old}
    assert {cs["version"] for cs in by_type.get("CodeSystem", [])} <= {old}


@pytest.mark.skipif("2026.7.0" not in MII_PRO_RETAINED_VERSIONS, reason="needs retained 2026.7.0")
async def test_content_dropped_upstream_survives_in_retained_version(fhir_server):
    """QLQ-C30 variant-a was removed in 2027; it still resolves at 2026.7.0
    (and only there), so QuestionnaireResponses pinned to it keep a target."""
    url = f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-eortc-qlq-c30-variant-a"
    assert await _count(fhir_server, "Questionnaire", url, "2026.7.0") == 1
    assert await _count(fhir_server, "Questionnaire", url, MII_PRO_VERSION) == 0


async def test_retained_versions_do_not_bring_observationdefinitions(fhir_server):
    """R4 ObservationDefinition has no canonical|version; the loader keeps the
    current version's copy and must not create a second one per id."""
    r = await fhir_server.get("/ObservationDefinition", params={"_summary": "count"})
    total = r.json().get("total", 0)
    # One per MII PRO OD (47 at 2027.0.0-ballot.1) plus PRO Library's own.
    assert 40 <= total <= 70, f"unexpected ObservationDefinition count {total} — duplicates from a retained version?"
