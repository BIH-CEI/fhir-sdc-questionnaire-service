"""DependencyResolver reference extraction and PackageService bundle shaping.

No HAPI involved: the resolver's network path (fetch_canonical) is driven
by a stub service so the de-duplication / warning logic can be pinned.
"""
import pytest

from app.services.package_service import (
    MAX_BUNDLE_ENTRIES,
    DependencyResolver,
    PackageService,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def resolver():
    return DependencyResolver(package_service=None)


def test_extract_valueset_refs_walks_nested_items(resolver):
    q = {"item": [
        {"linkId": "1", "answerValueSet": "http://x/VS/a"},
        {"linkId": "g", "item": [
            {"linkId": "g.1", "answerValueSet": "http://x/VS/b"},
            {"linkId": "g.2", "item": [{"linkId": "g.2.1", "answerValueSet": "#contained"}]},
        ]},
    ]}
    assert resolver.extract_valueset_refs(q) == ["http://x/VS/a", "http://x/VS/b", "#contained"]


def test_extract_codesystem_refs_from_compose_include(resolver):
    vs = {"compose": {"include": [
        {"system": "http://loinc.org"},
        {"valueSet": ["http://x/VS/other"]},  # no system → ignored
        {"system": "http://x/CS/local"},
    ]}}
    assert resolver.extract_codesystem_refs(vs) == ["http://loinc.org", "http://x/CS/local"]


def test_extract_library_refs_accepts_cqf_and_sdc_forms(resolver):
    q = {"extension": [
        {"url": "http://hl7.org/fhir/StructureDefinition/cqf-library",
         "valueCanonical": "http://x/Library/a|1.0"},
        {"url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-library",
         "valueReference": {"reference": "Library/b"}},
        {"url": "http://other/ext", "valueCanonical": "http://x/Library/ignored"},
    ]}
    assert resolver.extract_library_refs(q) == ["http://x/Library/a|1.0", "Library/b"]


def test_extract_structuremap_refs(resolver):
    q = {"extension": [
        {"url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-targetStructureMap",
         "valueCanonical": "http://x/StructureMap/m"},
    ]}
    assert resolver.extract_structuremap_refs(q) == ["http://x/StructureMap/m"]


class _StubService(PackageService):
    """PackageService with the HTTP layer replaced: answers fetch_resource
    from a canonical → resource map and records every lookup so call
    de-duplication can be asserted. find_canonical/pick_version stay real."""

    def __init__(self, resources: dict):  # noqa: D107 — no httpx client
        self.hapi_base = "http://unused"
        self.resources = resources
        self.calls = []

    async def fetch_resource(self, path, params=None):
        self.calls.append((path, params))
        url = (params or {}).get("url")
        version = (params or {}).get("version")
        res = self.resources.get(url)
        if res is None or (version and res.get("version") != version):
            return {"resourceType": "Bundle", "total": 0}
        return {"resourceType": "Bundle", "total": 1, "entry": [{"resource": res}]}


async def test_resolver_dedupes_shared_codesystem_and_skips_contained():
    cs = {"resourceType": "CodeSystem", "url": "http://x/CS/shared"}
    vs1 = {"resourceType": "ValueSet", "url": "http://x/VS/1",
           "compose": {"include": [{"system": "http://x/CS/shared"}]}}
    vs2 = {"resourceType": "ValueSet", "url": "http://x/VS/2",
           "compose": {"include": [{"system": "http://x/CS/shared"}]}}
    svc = _StubService({cs["url"]: cs, vs1["url"]: vs1, vs2["url"]: vs2})
    resolver = DependencyResolver(svc)

    q = {"item": [
        {"linkId": "1", "answerValueSet": "http://x/VS/1"},
        {"linkId": "2", "answerValueSet": "http://x/VS/2"},
        {"linkId": "3", "answerValueSet": "http://x/VS/1"},   # duplicate
        {"linkId": "4", "answerValueSet": "#inline"},          # contained
    ]}
    deps = await resolver.resolve_all_dependencies(q)

    urls = [d["url"] for d in deps]
    assert urls == ["http://x/VS/1", "http://x/CS/shared", "http://x/VS/2"]
    assert resolver.warnings == []
    looked_up = [p["url"] for _, p in svc.calls]
    assert looked_up.count("http://x/CS/shared") == 1
    assert "#inline" not in looked_up


async def test_resolver_warns_on_missing_valueset_but_not_on_loinc_snomed():
    vs = {"resourceType": "ValueSet", "url": "http://x/VS/ext",
          "compose": {"include": [{"system": "http://loinc.org"},
                                  {"system": "http://snomed.info/sct"},
                                  {"system": "http://x/CS/missing"}]}}
    resolver = DependencyResolver(_StubService({vs["url"]: vs}))

    q = {"item": [{"linkId": "1", "answerValueSet": "http://x/VS/ext"},
                  {"linkId": "2", "answerValueSet": "http://x/VS/gone"}]}
    await resolver.resolve_all_dependencies(q)

    by_severity = {}
    for w in resolver.warnings:
        by_severity.setdefault(w["severity"], []).append(w["diagnostics"])
    assert by_severity["warning"] == ["Referenced ValueSet not found: http://x/VS/gone"]
    assert by_severity["information"] == ["Referenced CodeSystem not found: http://x/CS/missing"]


async def test_resolver_follows_versioned_canonical_and_nested_library():
    lib_a = {"resourceType": "Library", "url": "http://x/Library/a", "version": "1.0",
             "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/cqf-library",
                            "valueCanonical": "http://x/Library/b"}]}
    lib_b = {"resourceType": "Library", "url": "http://x/Library/b"}
    svc = _StubService({lib_a["url"]: lib_a, lib_b["url"]: lib_b})
    resolver = DependencyResolver(svc)

    q = {"extension": [{"url": "http://hl7.org/fhir/StructureDefinition/cqf-library",
                        "valueCanonical": "http://x/Library/a|1.0"}]}
    deps = await resolver.resolve_all_dependencies(q)

    assert [d["url"] for d in deps] == ["http://x/Library/a", "http://x/Library/b"]
    first_call = svc.calls[0][1]
    assert first_call == {"url": "http://x/Library/a", "version": "1.0"}


async def test_build_bundle_enforces_entry_limit():
    many = [{"resourceType": "ValueSet", "url": f"http://x/VS/{i}"} for i in range(MAX_BUNDLE_ENTRIES)]
    svc = _StubService({vs["url"]: vs for vs in many})

    q = {"resourceType": "Questionnaire",
         "item": [{"linkId": str(i), "answerValueSet": vs["url"]} for i, vs in enumerate(many)]}
    with pytest.raises(ValueError, match="entry count"):
        await svc.build_bundle(q, include_dependencies=True)


def test_create_bundle_shape():
    bundle = PackageService("http://unused").create_bundle([{"resource": {"resourceType": "Questionnaire"}}])
    assert bundle["type"] == "collection"
    assert bundle["meta"]["tag"][0]["code"] == "questionnaire-package"
    assert bundle["timestamp"].endswith("Z")
