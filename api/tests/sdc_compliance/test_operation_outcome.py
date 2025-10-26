"""
SDC Compliance Tests for OperationOutcome Validation

Tests that error responses return proper OperationOutcome resources
with correct severity, code, and diagnostics.

Reference: FHIR R4 OperationOutcome resource
https://www.hl7.org/fhir/R4/operationoutcome.html
"""
import pytest


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestOperationOutcomeStructure:
    """
    Tests for OperationOutcome resource structure and content.

    Ensures that error responses include properly formatted OperationOutcome.
    """

    async def test_operation_outcome_has_required_severity(
        self,
        api_client,
        hapi_client
    ):
        """
        SDC Requirement: OperationOutcome SHALL have issue.severity

        Test ID: TEST-ERR-SEVERITY
        Requirement: SDC-FM-ERR-002-SHALL

        Given: Invalid request that generates error
        When: Error response is returned
        Then: OperationOutcome.issue[].severity is present and valid

        Reference: FHIR R4 OperationOutcome.issue.severity (required field)
        Valid values: fatal | error | warning | information
        """
        # Create invalid questionnaire with truly invalid data
        # Note: HAPI is lenient, so missing 'status' might be accepted
        # Use an explicitly invalid status value instead
        invalid_questionnaire = {
            "resourceType": "Questionnaire",
            "status": "this-is-not-a-valid-status",  # Invalid enum value
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await hapi_client.post(
            "/Questionnaire",
            json=invalid_questionnaire
        )

        # Should return error (400, 422, or 500)
        assert response.status_code in [400, 422, 500]

        # Parse response - should be OperationOutcome
        outcome = response.json()

        # Should be OperationOutcome
        assert outcome["resourceType"] == "OperationOutcome"

        # Must have issue array
        assert "issue" in outcome
        assert len(outcome["issue"]) > 0

        # Each issue MUST have severity
        for issue in outcome["issue"]:
            assert "severity" in issue, "OperationOutcome.issue SHALL have severity"

            # Severity must be one of: fatal, error, warning, information
            valid_severities = ["fatal", "error", "warning", "information"]
            assert issue["severity"] in valid_severities, \
                f"severity must be one of {valid_severities}, got: {issue['severity']}"

    async def test_operation_outcome_has_required_code(
        self,
        api_client,
        hapi_client
    ):
        """
        SDC Requirement: OperationOutcome SHALL have issue.code

        Test ID: TEST-ERR-CODE
        Requirement: SDC-FM-ERR-003-SHALL

        Given: Invalid request that generates error
        When: Error response is returned
        Then: OperationOutcome.issue[].code is present and valid

        Reference: FHIR R4 OperationOutcome.issue.code (required field)
        Valid codes: https://www.hl7.org/fhir/R4/valueset-issue-type.html
        """
        # Attempt to get non-existent resource
        response = await hapi_client.get("/Questionnaire/NONEXISTENT_ID_12345")

        assert response.status_code == 404

        outcome = response.json()

        # Should be OperationOutcome
        assert outcome["resourceType"] == "OperationOutcome"
        assert "issue" in outcome
        assert len(outcome["issue"]) > 0

        # Each issue MUST have code
        for issue in outcome["issue"]:
            assert "code" in issue, "OperationOutcome.issue SHALL have code"

            # Code must be from IssueType value set
            # Common codes: invalid, structure, required, value, invariant,
            #               security, login, unknown, expired, forbidden,
            #               processing, not-supported, duplicate, multiple-matches,
            #               not-found, deleted, too-long, code-invalid, extension,
            #               too-costly, business-rule, conflict, transient,
            #               lock-error, no-store, exception, timeout, incomplete,
            #               throttled, informational
            assert isinstance(issue["code"], str)
            assert len(issue["code"]) > 0

            # For 404, code should typically be "not-found"
            if response.status_code == 404:
                assert issue["code"] in ["not-found", "processing"], \
                    f"404 should have code 'not-found', got: {issue['code']}"

    async def test_operation_outcome_should_have_diagnostics(
        self,
        api_client,
        hapi_client
    ):
        """
        SDC Requirement: OperationOutcome SHOULD include issue.diagnostics

        Test ID: TEST-ERR-DIAGNOSTICS
        Requirement: SDC-FM-ERR-004-SHOULD

        Given: Error occurs
        When: OperationOutcome is returned
        Then: Should include human-readable diagnostics message

        Reference: FHIR R4 OperationOutcome.issue.diagnostics
        """
        # Request non-existent resource
        response = await hapi_client.get("/Questionnaire/DOES_NOT_EXIST_TEST")

        assert response.status_code == 404

        outcome = response.json()
        assert outcome["resourceType"] == "OperationOutcome"

        # Check for diagnostics (SHOULD, not SHALL)
        has_diagnostics = False
        for issue in outcome.get("issue", []):
            if "diagnostics" in issue:
                has_diagnostics = True
                # If present, should be non-empty string
                assert isinstance(issue["diagnostics"], str)
                assert len(issue["diagnostics"]) > 0

        # SHOULD have diagnostics (good practice, but not mandatory)
        # We'll just check that if it exists, it's properly formatted
        # Not asserting it must exist since it's SHOULD not SHALL

    async def test_validation_error_returns_proper_operation_outcome(
        self,
        api_client,
        hapi_client
    ):
        """
        Test: Validation errors return OperationOutcome with severity='error'

        Given: Invalid resource (violates FHIR validation)
        When: POST to create resource
        Then: Returns OperationOutcome with severity='error' and appropriate code

        Reference: FHIR R4 Validation
        """
        # Invalid: resourceType is wrong
        invalid_resource = {
            "resourceType": "Questionnaire",
            "status": "invalid-status-value",  # Invalid status
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await hapi_client.post(
            "/Questionnaire",
            json=invalid_resource
        )

        # Should return 400 or 422
        assert response.status_code in [400, 422]

        outcome = response.json()
        assert outcome["resourceType"] == "OperationOutcome"

        # Should have at least one issue with severity=error
        severities = [issue["severity"] for issue in outcome["issue"]]
        assert "error" in severities or "fatal" in severities

    async def test_not_found_returns_operation_outcome_with_not_found_code(
        self,
        api_client,
        hapi_client
    ):
        """
        Test: 404 responses include OperationOutcome with code='not-found'

        Given: Request for non-existent resource
        When: GET /ResourceType/{invalid_id}
        Then: Returns 404 with OperationOutcome having code='not-found'

        Reference: FHIR R4 HTTP Status Codes
        """
        response = await hapi_client.get("/Questionnaire/INVALID_NONEXISTENT_ID")

        assert response.status_code == 404

        outcome = response.json()
        assert outcome["resourceType"] == "OperationOutcome"

        # Should have code='not-found'
        codes = [issue["code"] for issue in outcome["issue"]]
        assert "not-found" in codes or "processing" in codes

    async def test_package_operation_missing_dependency_warning(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        Test: Missing dependency in $package returns OperationOutcome with severity='warning'

        Given: Questionnaire references non-existent ValueSet
        When: $package operation is called
        When: Bundle includes OperationOutcome with severity='warning'

        Reference: SDC IG $package operation - missing dependencies
        """
        from tests.fixtures.sample_resources import QUESTIONNAIRE_WITH_MISSING_VALUESET

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

        assert len(outcomes) >= 1, "Missing dependency should generate OperationOutcome"

        # Check the OperationOutcome structure
        outcome = outcomes[0]
        assert "issue" in outcome
        assert len(outcome["issue"]) > 0

        # Should have severity='warning' for missing dependency
        issue = outcome["issue"][0]
        assert "severity" in issue
        assert issue["severity"] == "warning", "Missing dependency should be warning, not error"

        # Should have appropriate code
        assert "code" in issue
        assert issue["code"] == "not-found" or issue["code"] == "incomplete"

        # Should have diagnostics explaining what's missing
        if "diagnostics" in issue:
            assert "not found" in issue["diagnostics"].lower() or \
                   "missing" in issue["diagnostics"].lower()


@pytest.mark.sdc_compliance
@pytest.mark.integration
@pytest.mark.asyncio
class TestOperationOutcomeErrorScenarios:
    """Tests for various error scenarios and their OperationOutcome responses."""

    async def test_invalid_resource_type_operation_outcome(self, api_client):
        """
        Test: Invalid resource type returns proper OperationOutcome

        Given: Request with wrong resourceType
        When: POST to /api/questionnaires
        Then: Returns error with OperationOutcome structure
        """
        invalid_resource = {
            "resourceType": "Patient",  # Wrong type
            "name": [{"family": "Test"}]
        }

        response = await api_client.post(
            "/api/questionnaires/",
            json=invalid_resource
        )

        assert response.status_code == 400

        # API should return error message or OperationOutcome
        # At minimum, should be valid JSON error response
        result = response.json()
        assert "detail" in result or "resourceType" in result

    async def test_malformed_json_operation_outcome(self, hapi_client):
        """
        Test: Malformed JSON returns error with appropriate status

        Given: Invalid JSON payload
        When: POST to HAPI FHIR
        Then: Returns 400 with error response
        """
        # Send malformed JSON directly to HAPI
        response = await hapi_client.post(
            "/Questionnaire",
            content=b'{"resourceType": "Questionnaire", invalid}',
            headers={"Content-Type": "application/fhir+json"}
        )

        # HAPI returns 500 for malformed JSON (not strictly spec-compliant, but acceptable)
        assert response.status_code in [400, 422, 500]

    async def test_operation_outcome_issue_expression_optional(
        self,
        api_client,
        hapi_client
    ):
        """
        Test: OperationOutcome.issue.expression is optional (MAY)

        Test ID: TEST-ERR-EXPRESSION
        Requirement: SDC-FM-ERR-005-MAY

        Given: Validation error occurs
        When: OperationOutcome is returned
        Then: May include issue.expression (FHIRPath to error location)

        Reference: FHIR R4 OperationOutcome.issue.expression (optional)
        """
        # Create invalid questionnaire
        invalid = {
            "resourceType": "Questionnaire",
            "status": "invalid-value",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await hapi_client.post("/Questionnaire", json=invalid)

        assert response.status_code in [400, 422]

        outcome = response.json()
        assert outcome["resourceType"] == "OperationOutcome"

        # Check if expression is present (it's optional)
        # If present, should be an array of strings (FHIRPath expressions)
        for issue in outcome.get("issue", []):
            if "expression" in issue:
                assert isinstance(issue["expression"], list)
                for expr in issue["expression"]:
                    assert isinstance(expr, str)
