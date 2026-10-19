"""HAPI's OperationOutcome responses — pinned to observed behaviour.

Reference: FHIR R4 OperationOutcome
https://www.hl7.org/fhir/R4/operationoutcome.html
"""
import pytest

pytestmark = [pytest.mark.upstream, pytest.mark.sdc_compliance, pytest.mark.asyncio]

VALID_SEVERITIES = {"fatal", "error", "warning", "information"}


async def test_invalid_enum_value_returns_400_operation_outcome(fhir_server):
    """Parse-level errors are caught even with validation off."""
    response = await fhir_server.post(
        "/Questionnaire",
        json={"resourceType": "Questionnaire", "status": "this-is-not-a-valid-status",
              "item": [{"linkId": "1", "text": "Q", "type": "string"}]},
    )

    assert response.status_code == 400
    outcome = response.json()
    assert outcome["resourceType"] == "OperationOutcome"
    assert outcome["issue"]
    for issue in outcome["issue"]:
        assert issue["severity"] in VALID_SEVERITIES
        assert issue["code"]
    assert outcome["issue"][0]["severity"] == "error"
    assert "PublicationStatus" in outcome["issue"][0]["diagnostics"]


async def test_missing_required_field_is_accepted_with_validation_off(fhir_server, clean_questionnaire):
    """Validation is off by design (see hapi-config/application.yaml). A
    Questionnaire without the required `status` is stored. Documents the
    guarantee the stack does NOT give; do not "fix" by enabling validation."""
    response = await fhir_server.post(
        "/Questionnaire",
        json={"resourceType": "Questionnaire", "item": [{"linkId": "1", "text": "Q", "type": "string"}]},
    )
    assert response.status_code == 201
    await fhir_server.delete(f"/Questionnaire/{response.json()['id']}")


async def test_not_found_returns_404_with_diagnostics(fhir_server):
    response = await fhir_server.get("/Questionnaire/NONEXISTENT_ID_12345")

    assert response.status_code == 404
    outcome = response.json()
    assert outcome["resourceType"] == "OperationOutcome"
    issue = outcome["issue"][0]
    assert issue["severity"] == "error"
    # HAPI reports 'processing' here rather than the more specific 'not-found'.
    assert issue["code"] in ("not-found", "processing")
    assert "NONEXISTENT_ID_12345" in issue["diagnostics"]


async def test_malformed_json_returns_400(fhir_server):
    response = await fhir_server.post(
        "/Questionnaire",
        content=b'{"resourceType": "Questionnaire", invalid}',
        headers={"Content-Type": "application/fhir+json"},
    )
    assert response.status_code == 400
    assert response.json()["resourceType"] == "OperationOutcome"
