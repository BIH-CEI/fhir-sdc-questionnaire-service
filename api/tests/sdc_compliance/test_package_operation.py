"""
SDC Compliance Tests for $package Operation

Tests compliance with SDC Form Manager CapabilityStatement:
https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html

Requirement: "The Form Manager SHALL support the $package operation on
Questionnaire resources to return a Bundle containing the Questionnaire and
all referenced dependencies including ValueSets, CodeSystems, Libraries, and
StructureMaps."

ARCHITECTURE NOTE
-----------------
- These tests use `api_client` which targets the FastAPI sidecar (port 8001).
  The sidecar implements a custom $package via PackageService.
- HAPI FHIR (port 8081) is storage only — its native $package is partial
  (see TestDependencyResolution.test_hapi_native_package_is_partial).
- We are testing our SDC-conformant implementation, not HAPI's capabilities.

DATA STRATEGY
-------------
The container ships MII PRO 2026.3.0 with all Questionnaires/ValueSets/
CodeSystems pre-loaded at boot. Tests anchor on real PRO content by
canonical URL via the `pro_questionnaires` fixture (see conftest.py),
which keeps tests deterministic and removes the fragile upload-then-resolve
dance that plagued the earlier example.org-based fixtures.

The chain we exercise for transitive-dep tests:
    Questionnaire mii-qst-pro-eortc-qlq-c30-variant-a
      → ValueSet mii-vs-pro-eortc-qlq-c30-scale-4pt
      → ValueSet mii-vs-pro-eortc-qlq-c30-scale-7pt
        → CodeSystem mii-cs-pro-eortc-qlq-c30 (shared by both VS)

Synthetic fixtures (`clean_questionnaire`, `sample_resources`) are kept
only for scenarios MII PRO does not exercise: missing-dependency warnings,
circular references, library-extension references, and deep-nested chains
constructed solely for the test.
"""
import pytest
from tests.fixtures.sample_resources import (
    QUESTIONNAIRE_WITH_MISSING_VALUESET,
    SIMPLE_TEXT_QUESTIONNAIRE,
    QUESTIONNAIRE_WITH_LIBRARY,
    SAMPLE_LIBRARY,
)


# Canonical URLs of the MII PRO ValueSets and CodeSystem we expect
# $package to traverse to from qlq-c30-variant-a.
QLQ_C30_VS_4PT = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"
QLQ_C30_VS_7PT = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-7pt"
QLQ_C30_CS     = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/CodeSystem/mii-cs-pro-eortc-qlq-c30"


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestSDCPackageOperationCompliance:
    """
    SDC Form Manager $package operation compliance test suite.

    Each test references specific SDC IG requirements.
    """

    async def test_package_returns_collection_bundle(self, api_client, pro_questionnaires):
        """
        SDC Requirement: $package SHALL return Bundle with type='collection'

        Reference: SDC IG Section 3.2.1, OperationDefinition-questionnaire-package
        """
        phq9_id = pro_questionnaires["phq_9"]["id"]

        response = await api_client.get(f"/api/questionnaires/{phq9_id}/$package")

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert "timestamp" in bundle
        assert "entry" in bundle
        assert len(bundle["entry"]) >= 1

    async def test_questionnaire_is_first_entry(self, api_client, pro_questionnaires):
        """
        SDC Requirement: Questionnaire SHOULD be first entry in bundle

        Reference: SDC IG Best Practices for Bundle ordering
        """
        phq9 = pro_questionnaires["phq_9"]

        response = await api_client.get(f"/api/questionnaires/{phq9['id']}/$package")
        bundle = response.json()

        first_entry = bundle["entry"][0]["resource"]
        assert first_entry["resourceType"] == "Questionnaire"
        assert first_entry["id"] == phq9["id"]
        assert first_entry["url"] == phq9["url"]

    async def test_includes_referenced_valuesets(self, api_client, pro_questionnaires):
        """
        SDC Requirement: SHALL include all referenced ValueSets

        Anchor: qlq-c30-variant-a binds 2 external answerValueSets
        (scale-4pt, scale-7pt). Both MUST appear in the bundle.

        Reference: SDC IG Section 3.2.1
        """
        q_id = pro_questionnaires["qlq_c30_variant_a"]["id"]

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]

        assert len(valuesets) >= 2, (
            f"Expected ≥2 ValueSets (scale-4pt + scale-7pt), got {len(valuesets)}"
        )

        valueset_urls = {vs.get("url") for vs in valuesets}
        assert QLQ_C30_VS_4PT in valueset_urls
        assert QLQ_C30_VS_7PT in valueset_urls

    async def test_includes_referenced_codesystems(self, api_client, pro_questionnaires):
        """
        SDC Requirement: SHALL include CodeSystems referenced by ValueSets
        (transitive dependency resolution)

        Anchor: qlq-c30-variant-a → 2 VS → both bind CodeSystem
        mii-cs-pro-eortc-qlq-c30. The CS MUST appear in the bundle exactly
        once even though two VS reference it.

        Reference: SDC IG Section 3.2.1 — Transitive dependencies
        """
        q_id = pro_questionnaires["qlq_c30_variant_a"]["id"]

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        codesystems = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "CodeSystem"
        ]

        assert len(codesystems) >= 1, (
            f"Expected ≥1 CodeSystem (mii-cs-pro-eortc-qlq-c30), got {len(codesystems)}"
        )

        codesystem_urls = [cs.get("url") for cs in codesystems]
        assert QLQ_C30_CS in codesystem_urls
        # Same CS referenced by 4pt + 7pt VS — packager MUST de-duplicate.
        assert codesystem_urls.count(QLQ_C30_CS) == 1, (
            "CodeSystem appears more than once — transitive de-duplication broken"
        )

    async def test_missing_dependency_returns_operation_outcome(
        self, api_client, clean_questionnaire
    ):
        """
        SDC Requirement: Missing dependencies SHALL generate OperationOutcome
        with severity='warning'

        Reference: SDC IG Section 3.2.1 - Error Handling

        NOTE: kept synthetic — MII PRO ships internally consistent content,
        so a "missing dependency" cannot occur with real data.
        """
        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_MISSING_VALUESET)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        assert response.status_code == 200

        bundle = response.json()
        outcomes = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "OperationOutcome"
        ]

        assert len(outcomes) >= 1
        issue = outcomes[0]["issue"][0]
        assert issue["severity"] == "warning"
        assert issue["code"] == "not-found"
        assert "not found" in issue["diagnostics"].lower()

    async def test_supports_include_dependencies_parameter(
        self, api_client, pro_questionnaires
    ):
        """
        SDC Requirement: SHALL support include-dependencies parameter

        Reference: OperationDefinition-questionnaire-package parameter definition
        """
        q_id = pro_questionnaires["qlq_c30_variant_a"]["id"]

        response_with = await api_client.get(
            f"/api/questionnaires/{q_id}/$package",
            params={"include-dependencies": True},
        )
        bundle_with = response_with.json()

        response_without = await api_client.get(
            f"/api/questionnaires/{q_id}/$package",
            params={"include-dependencies": False},
        )
        bundle_without = response_without.json()

        assert len(bundle_without["entry"]) < len(bundle_with["entry"])
        assert len(bundle_without["entry"]) == 1
        assert bundle_without["entry"][0]["resource"]["resourceType"] == "Questionnaire"

    async def test_instance_level_endpoint(self, api_client, pro_questionnaires):
        """
        SDC Requirement: SHALL support instance-level GET operation

        Endpoint: GET [base]/Questionnaire/[id]/$package

        Reference: OperationDefinition-questionnaire-package
        """
        phq9_id = pro_questionnaires["phq_9"]["id"]

        response = await api_client.get(f"/api/questionnaires/{phq9_id}/$package")

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"

    async def test_type_level_post_endpoint(self, api_client):
        """
        SDC Requirement: SHALL support type-level POST operation

        Endpoint: POST [base]/Questionnaire/$package

        The Questionnaire is provided in the request body and is NOT persisted.

        Reference: OperationDefinition-questionnaire-package
        """
        response = await api_client.post(
            "/api/questionnaires/$package",
            json=SIMPLE_TEXT_QUESTIONNAIRE,
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert bundle["entry"][0]["resource"]["resourceType"] == "Questionnaire"
        assert bundle["entry"][0]["resource"]["title"] == "Simple Text-Only Questionnaire"

    async def test_canonical_url_resolution(self, api_client, pro_questionnaires):
        """
        SDC Requirement: SHALL support canonical URL resolution

        Endpoint: GET [base]/Questionnaire/$package?url=[canonical]

        Real MII PRO canonical (no upload required — IG is loaded at boot).

        Reference: FHIR R4 Canonical URLs, SDC IG Section 3.2.1
        """
        phq9 = pro_questionnaires["phq_9"]

        response = await api_client.get(
            "/api/questionnaires/$package",
            params={"url": phq9["url"]},
        )

        assert response.status_code == 200
        bundle = response.json()
        q = bundle["entry"][0]["resource"]
        assert q["url"] == phq9["url"]

    async def test_version_specific_canonical_resolution(
        self, api_client, pro_questionnaires
    ):
        """
        SDC Requirement: SHALL support version-specific canonical URL resolution

        Reference: FHIR R4 Canonical URLs with version
        """
        phq9 = pro_questionnaires["phq_9"]

        response = await api_client.get(
            "/api/questionnaires/$package",
            params={"url": phq9["url"], "version": phq9["version"]},
        )

        assert response.status_code == 200
        bundle = response.json()
        q = bundle["entry"][0]["resource"]
        assert q["version"] == phq9["version"]

    async def test_nested_item_valueset_extraction(self, api_client, pro_questionnaires):
        """
        SDC Requirement: SHALL extract ValueSets from nested items

        Anchor: EORTC QLQ-C30 has a deeply nested item structure (subscale
        groups with item children that carry the answerValueSet binding).
        If the packager only walked top-level items, scale-4pt/-7pt would
        be missed.

        Reference: SDC IG Section 3.2.1 - Dependency Resolution
        """
        q_id = pro_questionnaires["qlq_c30_variant_a"]["id"]

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]
        valueset_urls = {vs.get("url") for vs in valuesets}

        assert QLQ_C30_VS_4PT in valueset_urls, (
            "scale-4pt VS missing — nested item walking likely broken"
        )
        assert QLQ_C30_VS_7PT in valueset_urls, (
            "scale-7pt VS missing — nested item walking likely broken"
        )

    async def test_questionnaire_without_dependencies(
        self, api_client, pro_questionnaires
    ):
        """
        Test: Questionnaire with no answerValueSet bindings produces a bundle
        with no ValueSets.

        Anchor: PHQ-9 uses inline `answerOption` only — there is nothing for
        $package to traverse to.
        """
        phq9_id = pro_questionnaires["phq_9"]["id"]

        response = await api_client.get(f"/api/questionnaires/{phq9_id}/$package")
        bundle = response.json()

        valuesets = [
            entry for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]
        assert len(valuesets) == 0, (
            f"PHQ-9 has no answerValueSet bindings; got {len(valuesets)} VS in bundle"
        )

        # The Questionnaire itself must always be there.
        assert any(
            entry["resource"]["resourceType"] == "Questionnaire"
            for entry in bundle["entry"]
        )

    async def test_bundle_has_sdc_tags(self, api_client, pro_questionnaires):
        """
        SDC Requirement: Bundle SHOULD have appropriate SDC tags

        Reference: SDC IG Bundle metadata requirements
        """
        phq9_id = pro_questionnaires["phq_9"]["id"]

        response = await api_client.get(f"/api/questionnaires/{phq9_id}/$package")
        bundle = response.json()

        assert "meta" in bundle
        assert "tag" in bundle["meta"]

        tags = bundle["meta"]["tag"]
        sdc_tags = [
            tag for tag in tags
            if "questionnaire-package" in tag.get("code", "")
        ]

        assert len(sdc_tags) >= 1

    async def test_questionnaire_not_found_returns_404(self, api_client):
        """
        Test: Non-existent Questionnaire ID returns 404
        """
        response = await api_client.get(
            "/api/questionnaires/NONEXISTENT_ID_12345/$package"
        )

        assert response.status_code == 404

    async def test_invalid_resource_type_returns_422(self, api_client):
        """
        Test: Non-Questionnaire resource returns 422
        """
        invalid_resource = {
            "resourceType": "Patient",
            "name": [{"family": "Doe"}],
        }

        response = await api_client.post(
            "/api/questionnaires/$package",
            json=invalid_resource,
        )

        assert response.status_code == 422


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestLibraryInclusion:
    """Tests for Library resource inclusion in packages.

    Kept synthetic: MII PRO 2026.3.0 Questionnaires do not declare cqf-library
    extensions, so this code path can only be exercised with a constructed
    fixture.
    """

    async def test_includes_library_references(
        self, api_client, hapi_client, clean_questionnaire
    ):
        """
        SDC Requirement: SHALL include Library resources referenced in extensions

        Reference: SDC IG Section 3.2.1 - Library dependencies
        """
        response = await hapi_client.post("/Library", json=SAMPLE_LIBRARY)
        library_id = response.json()["id"]

        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_LIBRARY)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        libraries = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "Library"
        ]

        assert len(libraries) >= 1

        await hapi_client.delete(f"/Library/{library_id}")


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestDependencyResolution:
    """Tests for complex dependency resolution scenarios.

    Kept synthetic: circular and arbitrarily deep chains do not occur in MII
    PRO content, so these scenarios are constructed inline.
    """

    async def test_circular_dependency_handling(
        self, api_client, hapi_client, clean_questionnaire, clean_valueset
    ):
        """
        SDC Requirement: SHOULD handle circular dependencies gracefully

        Test ID: TEST-PKG-CIRCULAR
        Requirement: SDC-FM-OP-PKG-014-SHOULD

        Given: Resources with circular references
        When: $package operation is called
        Then: Should include each resource only once (no infinite loop)
              AND should complete successfully

        Reference: SDC IG Section 3.2.1 - Circular dependency handling
        """
        valueset1 = {
            "resourceType": "ValueSet",
            "url": "http://example.org/ValueSet/circular-vs-1",
            "version": "1.0.0",
            "status": "active",
            "name": "CircularValueSet1",
            "title": "Circular ValueSet 1",
            "compose": {
                "include": [
                    {
                        "system": "http://loinc.org",
                        "concept": [{"code": "1234-5", "display": "Test Code"}],
                    },
                    {"valueSet": ["http://example.org/ValueSet/circular-vs-2"]},
                ]
            },
        }

        valueset2 = {
            "resourceType": "ValueSet",
            "url": "http://example.org/ValueSet/circular-vs-2",
            "version": "1.0.0",
            "status": "active",
            "name": "CircularValueSet2",
            "title": "Circular ValueSet 2",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "concept": [{"code": "9876-5", "display": "Another Code"}],
                    },
                    {"valueSet": ["http://example.org/ValueSet/circular-vs-1"]},
                ]
            },
        }

        await clean_valueset(valueset1)
        await clean_valueset(valueset2)

        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "active",
            "title": "Questionnaire with Circular Dependencies",
            "item": [
                {
                    "linkId": "1",
                    "text": "Question with circular ValueSet",
                    "type": "choice",
                    "answerValueSet": "http://example.org/ValueSet/circular-vs-1",
                }
            ],
        }

        q_id = await clean_questionnaire(questionnaire)

        response = await api_client.get(
            f"/api/questionnaires/{q_id}/$package", timeout=10.0
        )

        assert response.status_code == 200
        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]
        valueset_urls = [vs.get("url") for vs in valuesets]

        url_counts = {}
        for url in valueset_urls:
            url_counts[url] = url_counts.get(url, 0) + 1

        for url, count in url_counts.items():
            assert count == 1, f"ValueSet {url} appears {count} times (should be 1)"

        assert len(valuesets) >= 1, (
            "Should include at least the directly referenced ValueSet"
        )

    async def test_deep_nested_dependencies(
        self, api_client, hapi_client, clean_questionnaire,
        clean_valueset, clean_codesystem,
    ):
        """
        Test: Deep nested dependencies are fully resolved

        Given: Questionnaire -> ValueSet -> CodeSystem chain
        When: $package is called
        Then: All transitive dependencies are included

        Reference: SDC IG - Transitive dependency resolution
        """
        codesystem = {
            "resourceType": "CodeSystem",
            "url": "http://example.org/CodeSystem/deep-nested",
            "version": "1.0.0",
            "status": "active",
            "content": "complete",
            "concept": [
                {"code": "code1", "display": "Code 1"},
                {"code": "code2", "display": "Code 2"},
            ],
        }
        await clean_codesystem(codesystem)

        valueset = {
            "resourceType": "ValueSet",
            "url": "http://example.org/ValueSet/deep-nested",
            "version": "1.0.0",
            "status": "active",
            "compose": {
                "include": [{"system": "http://example.org/CodeSystem/deep-nested"}]
            },
        }
        await clean_valueset(valueset)

        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "active",
            "title": "Deep Nested Dependencies",
            "item": [
                {
                    "linkId": "1",
                    "text": "Question",
                    "type": "choice",
                    "answerValueSet": "http://example.org/ValueSet/deep-nested",
                }
            ],
        }
        q_id = await clean_questionnaire(questionnaire)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        resource_types = [
            entry["resource"]["resourceType"] for entry in bundle["entry"]
        ]

        assert "Questionnaire" in resource_types
        assert "ValueSet" in resource_types
        assert "CodeSystem" in resource_types

        valuesets = [
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "ValueSet"
        ]
        vs_urls = [vs.get("url") for vs in valuesets]
        assert "http://example.org/ValueSet/deep-nested" in vs_urls

        codesystems = [
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "CodeSystem"
        ]
        cs_urls = [cs.get("url") for cs in codesystems]
        assert "http://example.org/CodeSystem/deep-nested" in cs_urls

    @pytest.mark.xfail(
        reason="HAPI 8.4 CR's QuestionnairePackageProvider throws 500 on MII PRO "
        "2026.3.0 PHQ-9 (regressed from partial-bundle behaviour previously "
        "documented in commit eeb3492). Test kept as a regression sentinel: "
        "when HAPI either fixes the crash or starts returning an SDC-conformant "
        "Bundle, xfail flips to unexpected pass and we re-evaluate whether the "
        "FastAPI PackageService layer can be reduced to a thin proxy.",
        strict=False,
    )
    async def test_hapi_native_package_is_partial(self, hapi_client, pro_questionnaires):
        """
        Document the gap between HAPI's CR-provided $package and the
        SDC $package operation our FastAPI layer implements.

        HAPI 8.4 ships a QuestionnairePackageProvider that responds to $package.
        On MII PRO 2026.3.0 PHQ-9 it currently 500s (see xfail). When it did
        return a Bundle it was Bundle.type=transaction and omitted
        answerValueSet/CodeSystem/cqf-library/itemExtractionContext resolution.
        Our FastAPI PackageService fills those gaps — this test documents WHY
        that layer remains necessary.
        """
        phq9_id = pro_questionnaires["phq_9"]["id"]
        response = await hapi_client.get(f"/Questionnaire/{phq9_id}/$package")

        assert response.status_code == 200, \
            "HAPI 8.4+ should respond to $package via the CR module"

        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"
        assert bundle.get("type") == "transaction", \
            "HAPI native still returns transaction; SDC requires collection — " \
            "FastAPI layer remains responsible for SDC conformance."
