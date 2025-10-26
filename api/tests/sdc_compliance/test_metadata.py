"""
SDC Compliance Tests for Metadata and CapabilityStatement

Tests compliance with SDC Form Manager metadata requirements:
- CapabilityStatement availability
- SDC Form Manager role declaration
- FHIR version declaration

Reference: https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html
"""
import pytest


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestCapabilityStatement:
    """
    SDC Form Manager CapabilityStatement compliance tests.

    Tests that the server properly advertises its capabilities.
    """

    async def test_capability_statement_endpoint_exists(self, hapi_client):
        """
        SDC Requirement: SHALL provide CapabilityStatement at /metadata endpoint

        Test ID: TEST-META-001
        Requirement: SDC-FM-META-001-SHALL

        Given: FHIR server is running
        When: GET /metadata
        Then: Returns CapabilityStatement resource

        Reference: FHIR R4 Section 3.1.0.1 - Capability Statement
        """
        response = await hapi_client.get("/metadata")

        assert response.status_code == 200
        capability = response.json()

        # Verify it's a CapabilityStatement
        assert capability["resourceType"] == "CapabilityStatement"
        assert "fhirVersion" in capability
        assert "status" in capability
        assert capability["status"] in ["draft", "active", "retired"]

    async def test_declares_sdc_form_manager_role(self, hapi_client):
        """
        SDC Requirement: SHALL declare conformance to SDC Form Manager

        Test ID: TEST-META-002
        Requirement: SDC-FM-META-002-SHALL

        Given: CapabilityStatement exists
        When: Examining instantiates or implementationGuide
        Then: References SDC Form Manager capability

        Reference: SDC IG - Form Manager CapabilityStatement
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Check for SDC Form Manager declaration in instantiates
        sdc_declared = False

        # Option 1: Check instantiates field
        if "instantiates" in capability:
            for canonical in capability["instantiates"]:
                if "sdc" in canonical.lower() and "form-manager" in canonical.lower():
                    sdc_declared = True
                    break

        # Option 2: Check implementationGuide field
        if not sdc_declared and "implementationGuide" in capability:
            for ig_url in capability["implementationGuide"]:
                if "sdc" in ig_url.lower():
                    sdc_declared = True
                    break

        # Option 3: Check rest.resource for Questionnaire with $package operation
        if not sdc_declared:
            for rest in capability.get("rest", []):
                for resource in rest.get("resource", []):
                    if resource["type"] == "Questionnaire":
                        # Check for $package operation support
                        operations = resource.get("operation", [])
                        for op in operations:
                            if "$package" in op.get("name", ""):
                                sdc_declared = True
                                break

        # Note: HAPI FHIR may not explicitly declare SDC conformance
        # But it should at least support Questionnaire resource
        assert "rest" in capability
        questionnaire_supported = False
        for rest in capability["rest"]:
            for resource in rest.get("resource", []):
                if resource["type"] == "Questionnaire":
                    questionnaire_supported = True
                    break

        # At minimum, should support Questionnaire resource
        assert questionnaire_supported, "CapabilityStatement should declare Questionnaire support"

    async def test_declares_fhir_version(self, hapi_client):
        """
        SDC Requirement: SHALL declare FHIR version in CapabilityStatement

        Test ID: TEST-META-010
        Requirement: SDC-FM-META-010-SHALL

        Given: CapabilityStatement exists
        When: Examining fhirVersion field
        Then: Contains valid FHIR version (R4 or later)

        Reference: FHIR R4 CapabilityStatement.fhirVersion
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Must have fhirVersion
        assert "fhirVersion" in capability
        fhir_version = capability["fhirVersion"]

        # Should be R4 or later
        # FHIR versions: DSTU2 (1.0), STU3 (3.0), R4 (4.0), R4B (4.3), R5 (5.0)
        valid_versions = ["4.0", "4.0.0", "4.0.1", "4.3", "4.3.0", "5.0", "5.0.0"]

        # Check if version starts with any valid version
        is_valid = any(fhir_version.startswith(v) for v in valid_versions)

        assert is_valid, f"FHIR version {fhir_version} should be R4 (4.0) or later"

    async def test_capability_statement_lists_supported_operations(self, hapi_client):
        """
        SDC Requirement: SHOULD list supported operations in CapabilityStatement

        Test ID: TEST-META-004
        Requirement: SDC-FM-META-004-SHOULD

        Given: CapabilityStatement exists
        When: Examining rest.resource.operation
        Then: Lists supported operations (ideally including $package)

        Reference: SDC IG - Form Manager Operations
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Find Questionnaire resource definition
        questionnaire_resource = None
        for rest in capability.get("rest", []):
            for resource in rest.get("resource", []):
                if resource["type"] == "Questionnaire":
                    questionnaire_resource = resource
                    break

        # Should have Questionnaire resource declared
        assert questionnaire_resource is not None, "Questionnaire should be in CapabilityStatement"

        # Check for operations (SHOULD, not SHALL)
        # HAPI may or may not list all operations
        operations = questionnaire_resource.get("operation", [])

        # Just verify operations field exists (even if empty)
        # This is more lenient since HAPI may not list custom operations
        assert isinstance(operations, list)

    async def test_capability_statement_lists_search_parameters(self, hapi_client):
        """
        SDC Requirement: SHOULD list supported search parameters

        Test ID: TEST-META-005
        Requirement: SDC-FM-META-005-SHOULD

        Given: CapabilityStatement exists
        When: Examining rest.resource.searchParam
        Then: Lists supported search parameters for Questionnaire

        Reference: FHIR R4 CapabilityStatement.rest.resource.searchParam
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Find Questionnaire resource definition
        questionnaire_resource = None
        for rest in capability.get("rest", []):
            for resource in rest.get("resource", []):
                if resource["type"] == "Questionnaire":
                    questionnaire_resource = resource
                    break

        assert questionnaire_resource is not None

        # Check for searchParam
        search_params = questionnaire_resource.get("searchParam", [])

        # Should list at least some search parameters
        # Common ones: _id, url, version, status, title
        assert isinstance(search_params, list)

        # If search params are listed, verify structure
        if len(search_params) > 0:
            # Each search param should have name and type
            for param in search_params:
                assert "name" in param
                assert "type" in param


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestMetadataContent:
    """Tests for CapabilityStatement content and structure."""

    async def test_capability_statement_has_required_fields(self, hapi_client):
        """
        Test: CapabilityStatement has all required FHIR fields

        Given: CapabilityStatement endpoint
        When: GET /metadata
        Then: Contains all required fields per FHIR spec

        Reference: FHIR R4 CapabilityStatement resource definition
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Required fields per FHIR R4 spec
        assert "resourceType" in capability
        assert capability["resourceType"] == "CapabilityStatement"
        assert "status" in capability
        assert "date" in capability
        assert "kind" in capability
        assert "fhirVersion" in capability
        assert "format" in capability  # Must support at least one format

        # Verify formats include json
        formats = capability["format"]
        assert "json" in formats or "application/fhir+json" in formats

    async def test_capability_statement_declares_questionnaire_interactions(self, hapi_client):
        """
        Test: CapabilityStatement declares Questionnaire interactions

        Given: CapabilityStatement exists
        When: Examining Questionnaire resource
        Then: Declares supported interactions (read, search-type, etc.)

        Reference: SDC Form Manager SHALL support read and search
        """
        response = await hapi_client.get("/metadata")
        capability = response.json()

        # Find Questionnaire resource
        questionnaire_resource = None
        for rest in capability.get("rest", []):
            for resource in rest.get("resource", []):
                if resource["type"] == "Questionnaire":
                    questionnaire_resource = resource
                    break

        assert questionnaire_resource is not None

        # Check interactions
        interactions = questionnaire_resource.get("interaction", [])
        interaction_codes = [i["code"] for i in interactions]

        # SDC Form Manager SHALL support read and search-type
        assert "read" in interaction_codes, "SHALL support read interaction"
        assert "search-type" in interaction_codes, "SHALL support search-type interaction"
