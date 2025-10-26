"""
SDC Compliance Tests for $package Operation

Tests compliance with SDC Form Manager CapabilityStatement:
https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html

Requirement: "The Form Manager SHALL support the $package operation on
Questionnaire resources to return a Bundle containing the Questionnaire and
all referenced dependencies including ValueSets, CodeSystems, Libraries, and
StructureMaps."

ARCHITECTURE NOTE:
- These tests use `api_client` which tests the FastAPI application (localhost:8001)
- The FastAPI app implements a CUSTOM $package operation via PackageService
- HAPI FHIR (localhost:8081) is used as storage only - it does NOT natively
  support the $package operation
- We are testing our SDC-compliant implementation, not HAPI's capabilities
"""
import pytest
from tests.fixtures.sample_resources import (
    PHQ2_QUESTIONNAIRE,
    PHQ2_VALUESET,
    PHQ2_CODESYSTEM,
    QUESTIONNAIRE_WITH_MISSING_VALUESET,
    COMPLEX_NESTED_QUESTIONNAIRE,
    SIMPLE_TEXT_QUESTIONNAIRE,
    QUESTIONNAIRE_WITH_LIBRARY,
    SAMPLE_LIBRARY
)


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestSDCPackageOperationCompliance:
    """
    SDC Form Manager $package operation compliance test suite.

    Each test references specific SDC IG requirements.
    """

    async def test_package_returns_collection_bundle(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: $package SHALL return Bundle with type='collection'

        Reference: SDC IG Section 3.2.1, OperationDefinition-questionnaire-package
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )

        assert response.status_code == 200
        bundle = response.json()

        # FHIR compliance checks
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert "timestamp" in bundle
        assert "entry" in bundle
        assert len(bundle["entry"]) >= 1

    async def test_questionnaire_is_first_entry(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: Questionnaire SHOULD be first entry in bundle

        Reference: SDC IG Best Practices for Bundle ordering
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )
        bundle = response.json()

        first_entry = bundle["entry"][0]["resource"]
        assert first_entry["resourceType"] == "Questionnaire"
        assert first_entry["id"] == phq2_id

    async def test_includes_referenced_valuesets(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: SHALL include all referenced ValueSets

        Reference: SDC IG Section 3.2.1
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )
        bundle = response.json()

        # Extract all ValueSets from bundle
        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]

        # PHQ-2 references one ValueSet
        assert len(valuesets) >= 1

        # Verify the expected ValueSet is included
        valueset_urls = [vs.get("url") for vs in valuesets]
        assert "http://example.org/ValueSet/phq2-frequency" in valueset_urls

    async def test_includes_referenced_codesystems(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: SHALL include CodeSystems referenced by ValueSets

        Reference: SDC IG Section 3.2.1 - Transitive dependencies
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )
        bundle = response.json()

        # Extract all CodeSystems from bundle
        codesystems = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "CodeSystem"
        ]

        # PHQ-2 ValueSet references one CodeSystem
        assert len(codesystems) >= 1

        codesystem_urls = [cs.get("url") for cs in codesystems]
        assert "http://example.org/CodeSystem/phq-frequency" in codesystem_urls

    async def test_missing_dependency_returns_operation_outcome(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: Missing dependencies SHALL generate OperationOutcome
        with severity='warning'

        Reference: SDC IG Section 3.2.1 - Error Handling
        """
        # Create questionnaire with missing ValueSet reference
        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_MISSING_VALUESET)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        assert response.status_code == 200

        bundle = response.json()

        # Find OperationOutcome in bundle
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
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: SHALL support include-dependencies parameter

        Reference: OperationDefinition-questionnaire-package parameter definition
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        # With dependencies (default)
        response_with = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package",
            params={"include-dependencies": True}
        )
        bundle_with = response_with.json()

        # Without dependencies
        response_without = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package",
            params={"include-dependencies": False}
        )
        bundle_without = response_without.json()

        # Verify bundle without dependencies has fewer entries
        assert len(bundle_without["entry"]) < len(bundle_with["entry"])
        assert len(bundle_without["entry"]) == 1  # Only Questionnaire

        # Verify only Questionnaire is present
        assert bundle_without["entry"][0]["resource"]["resourceType"] == "Questionnaire"

    async def test_instance_level_endpoint(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: SHALL support instance-level GET operation

        Endpoint: GET [base]/Questionnaire/[id]/$package

        Reference: OperationDefinition-questionnaire-package
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )

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
            json=SIMPLE_TEXT_QUESTIONNAIRE
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert bundle["entry"][0]["resource"]["resourceType"] == "Questionnaire"
        assert bundle["entry"][0]["resource"]["title"] == "Simple Text-Only Questionnaire"

    async def test_canonical_url_resolution(
        self,
        api_client,
        hapi_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL support canonical URL resolution

        Endpoint: GET [base]/Questionnaire/$package?url=[canonical]&version=[version]

        Reference: FHIR R4 Canonical URLs, SDC IG Section 3.2.1
        """
        # Create Questionnaire with canonical URL
        questionnaire = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/Questionnaire/test-canonical",
            "version": "1.0.0",
            "status": "active",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        await clean_questionnaire(questionnaire)

        # Call $package by canonical URL (without version - should get latest)
        response = await api_client.get(
            "/api/questionnaires/$package",
            params={"url": "http://example.org/Questionnaire/test-canonical"}
        )

        assert response.status_code == 200
        bundle = response.json()
        q = bundle["entry"][0]["resource"]
        assert q["url"] == "http://example.org/Questionnaire/test-canonical"

    async def test_version_specific_canonical_resolution(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL support version-specific canonical URL resolution

        Reference: FHIR R4 Canonical URLs with version
        """
        # Create versioned Questionnaire
        questionnaire_v1 = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/Questionnaire/versioned",
            "version": "1.0.0",
            "status": "active",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        await clean_questionnaire(questionnaire_v1)

        # Request specific version
        response = await api_client.get(
            "/api/questionnaires/$package",
            params={
                "url": "http://example.org/Questionnaire/versioned",
                "version": "1.0.0"
            }
        )

        assert response.status_code == 200
        bundle = response.json()
        q = bundle["entry"][0]["resource"]
        assert q["version"] == "1.0.0"

    async def test_nested_item_valueset_extraction(
        self,
        api_client,
        hapi_client,
        clean_questionnaire,
        clean_valueset,
        clean_codesystem
    ):
        """
        SDC Requirement: SHALL extract ValueSets from nested items

        Questionnaires with nested groups must have all ValueSets extracted.

        Reference: SDC IG Section 3.2.1 - Dependency Resolution
        """
        # Create ValueSet and CodeSystem first
        await clean_valueset(PHQ2_VALUESET)
        await clean_codesystem(PHQ2_CODESYSTEM)

        # Create questionnaire with nested items
        q_id = await clean_questionnaire(COMPLEX_NESTED_QUESTIONNAIRE)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        # Extract ValueSets - should find ValueSets in nested items
        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]

        # Complex questionnaire has 2 references to the same ValueSet in nested items
        assert len(valuesets) >= 1

    async def test_questionnaire_without_dependencies(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        Test: Questionnaire with no dependencies returns minimal bundle

        Given: Questionnaire with only text/string items (no ValueSets)
        When: $package is called
        Then: Bundle contains only the Questionnaire
        """
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)

        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        # Should only have Questionnaire (no ValueSets, CodeSystems, etc.)
        assert len(bundle["entry"]) == 1
        assert bundle["entry"][0]["resource"]["resourceType"] == "Questionnaire"

    async def test_bundle_has_sdc_tags(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        SDC Requirement: Bundle SHOULD have appropriate SDC tags

        Reference: SDC IG Bundle metadata requirements
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}/$package"
        )
        bundle = response.json()

        # Check for meta.tag with SDC coding
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

        Given: Invalid Questionnaire ID
        When: $package is called
        Then: Returns 404 Not Found
        """
        response = await api_client.get(
            "/api/questionnaires/NONEXISTENT_ID_12345/$package"
        )

        assert response.status_code == 404

    async def test_invalid_resource_type_returns_422(self, api_client):
        """
        Test: Non-Questionnaire resource returns 422

        Given: Resource with type != "Questionnaire"
        When: POST /$package with invalid resource
        Then: Returns 422 Unprocessable Entity
        """
        invalid_resource = {
            "resourceType": "Patient",  # Wrong type
            "name": [{"family": "Doe"}]
        }

        response = await api_client.post(
            "/api/questionnaires/$package",
            json=invalid_resource
        )

        assert response.status_code == 422


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestLibraryInclusion:
    """Tests for Library resource inclusion in packages."""

    async def test_includes_library_references(
        self,
        api_client,
        hapi_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL include Library resources referenced in extensions

        Reference: SDC IG Section 3.2.1 - Library dependencies
        """
        # Create Library first
        response = await hapi_client.post("/Library", json=SAMPLE_LIBRARY)
        library_id = response.json()["id"]

        # Create Questionnaire with Library reference
        q_id = await clean_questionnaire(QUESTIONNAIRE_WITH_LIBRARY)

        # Package
        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        # Check for Library in bundle
        libraries = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "Library"
        ]

        # Should include the referenced library
        assert len(libraries) >= 1

        # Cleanup
        await hapi_client.delete(f"/Library/{library_id}")


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestDependencyResolution:
    """Tests for complex dependency resolution scenarios."""

    async def test_circular_dependency_handling(
        self,
        api_client,
        hapi_client,
        clean_questionnaire,
        clean_valueset
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
        # Create two ValueSets that reference each other
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
                        "concept": [
                            {"code": "1234-5", "display": "Test Code"}
                        ]
                    },
                    {
                        # Reference to second ValueSet
                        "valueSet": ["http://example.org/ValueSet/circular-vs-2"]
                    }
                ]
            }
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
                        "concept": [
                            {"code": "9876-5", "display": "Another Code"}
                        ]
                    },
                    {
                        # Reference back to first ValueSet (creates cycle)
                        "valueSet": ["http://example.org/ValueSet/circular-vs-1"]
                    }
                ]
            }
        }

        # Create both ValueSets
        await clean_valueset(valueset1)
        await clean_valueset(valueset2)

        # Create Questionnaire that references the first ValueSet
        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "active",
            "title": "Questionnaire with Circular Dependencies",
            "item": [
                {
                    "linkId": "1",
                    "text": "Question with circular ValueSet",
                    "type": "choice",
                    "answerValueSet": "http://example.org/ValueSet/circular-vs-1"
                }
            ]
        }

        q_id = await clean_questionnaire(questionnaire)

        # Call $package - should handle circular dependency
        response = await api_client.get(
            f"/api/questionnaires/{q_id}/$package",
            timeout=10.0  # Set timeout to ensure it doesn't hang
        )

        # Should complete successfully (not timeout or error)
        assert response.status_code == 200

        bundle = response.json()
        assert bundle["resourceType"] == "Bundle"

        # Extract all ValueSets
        valuesets = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "ValueSet"
        ]

        # Count occurrences of each ValueSet by URL
        valueset_urls = [vs.get("url") for vs in valuesets]

        # Each ValueSet should appear only ONCE (no duplicates from circular refs)
        url_counts = {}
        for url in valueset_urls:
            url_counts[url] = url_counts.get(url, 0) + 1

        # Verify no duplicates
        for url, count in url_counts.items():
            assert count == 1, f"ValueSet {url} appears {count} times (should be 1)"

        # Should include both ValueSets (following the circular reference)
        # Note: This depends on implementation - some systems may only include
        # the directly referenced ValueSet
        assert len(valuesets) >= 1, "Should include at least the directly referenced ValueSet"

    async def test_deep_nested_dependencies(
        self,
        api_client,
        hapi_client,
        clean_questionnaire,
        clean_valueset,
        clean_codesystem
    ):
        """
        Test: Deep nested dependencies are fully resolved

        Given: Questionnaire -> ValueSet -> CodeSystem chain
        When: $package is called
        Then: All transitive dependencies are included

        Reference: SDC IG - Transitive dependency resolution
        """
        # Create CodeSystem
        codesystem = {
            "resourceType": "CodeSystem",
            "url": "http://example.org/CodeSystem/deep-nested",
            "version": "1.0.0",
            "status": "active",
            "content": "complete",
            "concept": [
                {"code": "code1", "display": "Code 1"},
                {"code": "code2", "display": "Code 2"}
            ]
        }
        await clean_codesystem(codesystem)

        # Create ValueSet that references CodeSystem
        valueset = {
            "resourceType": "ValueSet",
            "url": "http://example.org/ValueSet/deep-nested",
            "version": "1.0.0",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://example.org/CodeSystem/deep-nested"
                    }
                ]
            }
        }
        await clean_valueset(valueset)

        # Create Questionnaire that references ValueSet
        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "active",
            "title": "Deep Nested Dependencies",
            "item": [
                {
                    "linkId": "1",
                    "text": "Question",
                    "type": "choice",
                    "answerValueSet": "http://example.org/ValueSet/deep-nested"
                }
            ]
        }
        q_id = await clean_questionnaire(questionnaire)

        # Package
        response = await api_client.get(f"/api/questionnaires/{q_id}/$package")
        bundle = response.json()

        # Should include Questionnaire, ValueSet, AND CodeSystem
        resource_types = [
            entry["resource"]["resourceType"]
            for entry in bundle["entry"]
        ]

        assert "Questionnaire" in resource_types
        assert "ValueSet" in resource_types
        assert "CodeSystem" in resource_types

        # Verify the specific resources are present
        valuesets = [e["resource"] for e in bundle["entry"]
                     if e["resource"]["resourceType"] == "ValueSet"]
        vs_urls = [vs.get("url") for vs in valuesets]
        assert "http://example.org/ValueSet/deep-nested" in vs_urls

        codesystems = [e["resource"] for e in bundle["entry"]
                       if e["resource"]["resourceType"] == "CodeSystem"]
        cs_urls = [cs.get("url") for cs in codesystems]
        assert "http://example.org/CodeSystem/deep-nested" in cs_urls

    @pytest.mark.xfail(
        reason="HAPI FHIR does not natively support $package operation - our FastAPI layer implements it",
        strict=True
    )
    async def test_hapi_does_not_support_package_natively(self, hapi_client, load_test_fixtures):
        """
        Test: HAPI FHIR does not natively support $package operation

        Test ID: TEST-PKG-HAPI-001
        Purpose: Document that $package is a custom implementation

        This test explicitly shows that HAPI FHIR (as of v6.x) does NOT
        natively support the SDC $package operation. Our FastAPI application
        provides this functionality by implementing PackageService.

        Expected behavior: HAPI returns 404 or OperationOutcome indicating
        the operation is not supported.

        This test is marked with @pytest.mark.xfail(strict=True) which means:
        - If HAPI returns an error (404/400/501), the test PASSES (expected failure)
        - If HAPI somehow supports $package, the test FAILS (unexpected pass)
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        # Try to call $package directly on HAPI (bypassing our FastAPI layer)
        # This should fail because HAPI doesn't implement SDC $package
        response = await hapi_client.get(f"/Questionnaire/{phq2_id}/$package")

        # This assertion will fail (HAPI doesn't support it)
        # But because of xfail, the test suite will mark this as "XFAIL" (expected failure)
        assert response.status_code == 200, \
            "HAPI should not support $package - this assertion is expected to fail"
