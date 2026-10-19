"""
$package — sidecar implementation (PackageService), end to end.

$package is defined by CRMI (hl7.fhir.uv.crmi 2.0.0, OperationDefinition
crmi-package); SDC 3.0.0/4.0.0 define no $package and their Form Manager
CapabilityStatement does not list one. CRMI: "The first resource returned in
the resulting package will be an outcome manifest" (Library asset-collection,
crmi-manifestlibrary) carrying the packaging messages (cqf-messages →
contained OperationOutcome); "Servers generating packages SHALL include all
the dependency resources referenced by the artifact that are known to the
server".

DATA STRATEGY
-------------
Tests anchor on real MII PRO content by canonical URL via the
`pro_questionnaires` fixture (conftest.py). The chain exercised for
transitive dependencies:

    Questionnaire mii-qst-pro-eortc-qlq-c30
      → ValueSet mii-vs-pro-eortc-qlq-c30-scale-4pt
      → ValueSet mii-vs-pro-eortc-qlq-c30-scale-7pt
        → CodeSystem mii-cs-pro-eortc-qlq-c30 (shared by both VS)

Synthetic fixtures are used only for what MII PRO does not exercise:
missing dependencies, circular references, Library references, contained
ValueSets, deep chains. HAPI's own (partial) $package is documented in
tests/upstream/test_hapi_native_package.py.
"""
import pytest

from tests.conftest import MII_PRO_BASE
from tests.fixtures.sample_resources import (
    QUESTIONNAIRE_WITH_LIBRARY,
    QUESTIONNAIRE_WITH_MISSING_VALUESET,
    SAMPLE_LIBRARY,
    SIMPLE_TEXT_QUESTIONNAIRE,
)

pytestmark = [pytest.mark.sdc_compliance, pytest.mark.integration, pytest.mark.asyncio]

QLQ_C30_VS_4PT = f"{MII_PRO_BASE}/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
QLQ_C30_VS_7PT = f"{MII_PRO_BASE}/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-7pt"
QLQ_C30_CS = f"{MII_PRO_BASE}/CodeSystem/mii-cs-pro-eortc-qlq-c30"


CRMI_MANIFEST = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-manifestlibrary"


def _manifest(bundle: dict) -> dict:
    """The outcome manifest — CRMI: always the first resource."""
    first = bundle["entry"][0]["resource"]
    assert first["resourceType"] == "Library" and CRMI_MANIFEST in first["meta"]["profile"], first
    return first


def _of_type(bundle: dict, rtype: str) -> list:
    """Packaged artifacts of a type (the manifest itself excluded)."""
    _manifest(bundle)
    return [e["resource"] for e in bundle["entry"][1:] if e["resource"]["resourceType"] == rtype]


def _messages(bundle: dict) -> list:
    """Packaging issues: the manifest's contained OperationOutcome."""
    manifest = _manifest(bundle)
    assert not [e for e in bundle["entry"] if e["resource"]["resourceType"] == "OperationOutcome"], \
        "messages belong in the manifest, not in a separate entry"
    return [i for c in manifest.get("contained", []) if c["resourceType"] == "OperationOutcome"
            for i in c["issue"]]


class TestSDCPackageOperationCompliance:

    async def test_package_returns_collection_bundle(self, api_client, pro_questionnaires):
        """SDC: $package SHALL return Bundle with type='collection'."""
        response = await api_client.get(f"/api/questionnaires/{pro_questionnaires['phq_9']['id']}/$package")

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert "timestamp" in bundle
        assert len(bundle["entry"]) >= 1

    async def test_outcome_manifest_first_then_questionnaire(self, api_client, pro_questionnaires):
        """CRMI: the outcome manifest is the first resource; it names the
        packaged Questionnaire (url|version) as its component."""
        phq9 = pro_questionnaires["phq_9"]
        bundle = (await api_client.get(f"/api/questionnaires/{phq9['id']}/$package")).json()

        manifest = _manifest(bundle)
        assert manifest["type"]["coding"][0]["code"] == "asset-collection"
        assert "content" not in manifest
        components = [r for r in manifest["relatedArtifact"] if r["type"] == "composed-of"]
        assert [c["resource"] for c in components] == [f"{phq9['url']}|{phq9['version']}"]

        second = bundle["entry"][1]["resource"]
        assert (second["resourceType"], second["id"], second["url"]) == ("Questionnaire", phq9["id"], phq9["url"])

    async def test_manifest_pins_dependency_versions(self, api_client, pro_questionnaires):
        """Every packaged dependency appears as depends-on with the exact
        url|version that was packaged — the consumer can verify the set."""
        q = pro_questionnaires["qlq_c30"]
        bundle = (await api_client.get(f"/api/questionnaires/{q['id']}/$package")).json()

        depends_on = {r["resource"] for r in _manifest(bundle)["relatedArtifact"] if r["type"] == "depends-on"}
        packaged = {f"{e['resource']['url']}|{e['resource']['version']}" for e in bundle["entry"][2:]}
        assert packaged <= depends_on, f"packaged but not in manifest: {packaged - depends_on}"
        assert f"{QLQ_C30_VS_4PT}|{q['version']}" in depends_on

    async def test_includes_referenced_valuesets_from_nested_items(self, api_client, pro_questionnaires):
        """SDC: SHALL include all referenced ValueSets, also from nested items.

        QLQ-C30 carries its answerValueSet bindings on items nested inside
        subscale groups — a top-level-only walk would miss both."""
        q = pro_questionnaires["qlq_c30"]
        bundle = (await api_client.get(f"/api/questionnaires/{q['id']}/$package")).json()

        urls = {vs.get("url") for vs in _of_type(bundle, "ValueSet")}
        assert {QLQ_C30_VS_4PT, QLQ_C30_VS_7PT} <= urls, f"got {urls}"
        # Version-aware resolution: the VS must belong to the same MII PRO
        # version as the Questionnaire.
        assert {vs.get("version") for vs in _of_type(bundle, "ValueSet")} == {q["version"]}

    async def test_includes_referenced_codesystems_once(self, api_client, pro_questionnaires):
        """SDC: SHALL include CodeSystems referenced by ValueSets (transitive),
        de-duplicated — both VS bind the same CS."""
        q_id = pro_questionnaires["qlq_c30"]["id"]
        bundle = (await api_client.get(f"/api/questionnaires/{q_id}/$package")).json()

        cs_urls = [cs.get("url") for cs in _of_type(bundle, "CodeSystem")]
        assert cs_urls.count(QLQ_C30_CS) == 1, f"CodeSystem count: {cs_urls}"

    async def test_missing_dependency_returns_operation_outcome_warning(self, api_client, clean_questionnaire):
        """Missing dependencies are reported as warnings in the manifest's OperationOutcome."""
        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_MISSING_VALUESET)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        assert response.status_code == 200

        issues = _messages(response.json())
        assert len(issues) == 1
        issue = issues[0]
        assert issue["severity"] == "warning"
        assert issue["code"] == "not-found"
        assert "DOES_NOT_EXIST" in issue["diagnostics"]

    async def test_include_dependencies_false_returns_questionnaire_only(self, api_client, pro_questionnaires):
        """SDC: SHALL support the include-dependencies parameter."""
        q_id = pro_questionnaires["qlq_c30"]["id"]
        with_deps = (await api_client.get(f"/api/questionnaires/{q_id}/$package")).json()
        without = (await api_client.get(
            f"/api/questionnaires/{q_id}/$package", params={"include-dependencies": False}
        )).json()

        assert len(with_deps["entry"]) > 2
        assert [e["resource"]["resourceType"] for e in without["entry"]] == ["Library", "Questionnaire"]
        assert [r["type"] for r in _manifest(without)["relatedArtifact"]] == ["composed-of"]

    async def test_type_level_post_does_not_persist(self, api_client, fhir_server):
        """SDC: SHALL support type-level POST; the body Questionnaire is not stored."""
        q = {**SIMPLE_TEXT_QUESTIONNAIRE, "url": "http://example.org/Questionnaire/package-post-probe"}
        response = await api_client.post("/api/questionnaires/$package", json=q)

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["type"] == "collection"
        assert bundle["entry"][1]["resource"]["title"] == q["title"]
        stored = await fhir_server.get("/Questionnaire", params={"url": q["url"], "_summary": "count"})
        assert stored.json().get("total", 0) == 0

    async def test_canonical_url_resolution(self, api_client, pro_questionnaires):
        """SDC: SHALL support resolution by canonical URL, with and without version."""
        phq9 = pro_questionnaires["phq_9"]

        unversioned = await api_client.get("/api/questionnaires/$package", params={"url": phq9["url"]})
        assert unversioned.status_code == 200
        assert unversioned.json()["entry"][1]["resource"]["url"] == phq9["url"]

        versioned = await api_client.get(
            "/api/questionnaires/$package", params={"url": phq9["url"], "version": phq9["version"]}
        )
        assert versioned.status_code == 200
        assert versioned.json()["entry"][1]["resource"]["version"] == phq9["version"]

    async def test_unknown_version_returns_404(self, api_client, pro_questionnaires):
        response = await api_client.get(
            "/api/questionnaires/$package",
            params={"url": pro_questionnaires["phq_9"]["url"], "version": "0.0.0-nope"},
        )
        assert response.status_code == 404

    async def test_questionnaire_without_bindings_has_no_valuesets(self, api_client, pro_questionnaires):
        """PHQ-9 uses inline answerOption only — nothing to traverse."""
        bundle = (await api_client.get(f"/api/questionnaires/{pro_questionnaires['phq_9']['id']}/$package")).json()
        assert _of_type(bundle, "ValueSet") == []
        assert _messages(bundle) == []

    async def test_bundle_has_sdc_package_tag(self, api_client, pro_questionnaires):
        bundle = (await api_client.get(f"/api/questionnaires/{pro_questionnaires['phq_9']['id']}/$package")).json()
        codes = [t.get("code") for t in bundle["meta"]["tag"]]
        assert "questionnaire-package" in codes

    async def test_questionnaire_not_found_returns_404(self, api_client):
        response = await api_client.get("/api/questionnaires/NONEXISTENT_ID_12345/$package")
        assert response.status_code == 404

    async def test_invalid_resource_type_returns_422(self, api_client):
        response = await api_client.post("/api/questionnaires/$package", json={"resourceType": "Patient"})
        assert response.status_code == 422


class TestDependencyResolution:
    """Scenarios MII PRO content does not exercise — constructed inline."""

    async def test_includes_library_references(self, api_client, clean_library, clean_questionnaire):
        """SDC: SHALL include Libraries referenced via cqf-library (versioned canonical)."""
        await clean_library(SAMPLE_LIBRARY)
        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_LIBRARY)

        bundle = (await api_client.get(f"/api/questionnaires/{q_id}/$package")).json()

        libraries = _of_type(bundle, "Library")
        assert [lib["url"] for lib in libraries] == [SAMPLE_LIBRARY["url"]]
        assert _messages(bundle) == []

    async def test_contained_valueset_is_not_resolved_externally(self, api_client, clean_questionnaire):
        """A `#fragment` answerValueSet is a contained resource; the packager
        must neither look it up on the server nor warn about it."""
        q = {
            "resourceType": "Questionnaire",
            "status": "active",
            "title": "Contained VS",
            "contained": [{
                "resourceType": "ValueSet", "id": "yesno", "status": "active",
                "compose": {"include": [{"system": "http://example.org/CodeSystem/yesno",
                                         "concept": [{"code": "y"}, {"code": "n"}]}]},
            }],
            "item": [{"linkId": "1", "type": "choice", "text": "Q", "answerValueSet": "#yesno"}],
        }
        q_id = await clean_questionnaire(q)

        bundle = (await api_client.get(f"/api/questionnaires/{q_id}/$package")).json()

        assert len(bundle["entry"]) == 2
        assert bundle["entry"][1]["resource"]["contained"][0]["id"] == "yesno"
        assert _messages(bundle) == []

    async def test_circular_valueset_includes_handled(self, api_client, clean_questionnaire, clean_valueset):
        """SDC: SHOULD handle circular references — each resource once, no hang."""
        vs1 = {"resourceType": "ValueSet", "url": "http://example.org/ValueSet/circular-vs-1",
               "version": "1.0.0", "status": "active", "name": "CircularValueSet1",
               "compose": {"include": [{"system": "http://loinc.org", "concept": [{"code": "1234-5"}]},
                                       {"valueSet": ["http://example.org/ValueSet/circular-vs-2"]}]}}
        vs2 = {"resourceType": "ValueSet", "url": "http://example.org/ValueSet/circular-vs-2",
               "version": "1.0.0", "status": "active", "name": "CircularValueSet2",
               "compose": {"include": [{"system": "http://snomed.info/sct", "concept": [{"code": "9876-5"}]},
                                       {"valueSet": ["http://example.org/ValueSet/circular-vs-1"]}]}}
        await clean_valueset(vs1)
        await clean_valueset(vs2)
        q_id = await clean_questionnaire({
            "resourceType": "Questionnaire", "status": "active", "title": "Circular",
            "item": [{"linkId": "1", "type": "choice", "text": "Q", "answerValueSet": vs1["url"]}],
        })

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package", timeout=10.0)

        assert response.status_code == 200
        urls = [vs["url"] for vs in _of_type(response.json(), "ValueSet")]
        assert urls == [vs1["url"]]
        # LOINC / SNOMED CodeSystems are external: absent and not warned about.
        assert _of_type(response.json(), "CodeSystem") == []
        assert _messages(response.json()) == []

    async def test_deep_nested_dependencies(self, api_client, clean_questionnaire, clean_valueset, clean_codesystem):
        """Questionnaire → ValueSet → CodeSystem chain fully resolved."""
        await clean_codesystem({"resourceType": "CodeSystem", "url": "http://example.org/CodeSystem/deep-nested",
                                "version": "1.0.0", "status": "active", "content": "complete",
                                "concept": [{"code": "code1"}, {"code": "code2"}]})
        await clean_valueset({"resourceType": "ValueSet", "url": "http://example.org/ValueSet/deep-nested",
                              "version": "1.0.0", "status": "active",
                              "compose": {"include": [{"system": "http://example.org/CodeSystem/deep-nested"}]}})
        q_id = await clean_questionnaire({
            "resourceType": "Questionnaire", "status": "active", "title": "Deep",
            "item": [{"linkId": "1", "type": "choice", "text": "Q",
                      "answerValueSet": "http://example.org/ValueSet/deep-nested"}],
        })

        bundle = (await api_client.get(f"/api/questionnaires/{q_id}/$package")).json()

        assert [e["resource"]["resourceType"] for e in bundle["entry"]] == ["Library", "Questionnaire", "ValueSet", "CodeSystem"]
        assert bundle["entry"][3]["resource"]["url"] == "http://example.org/CodeSystem/deep-nested"
