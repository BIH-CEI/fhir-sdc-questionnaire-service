"""Sidecar error handling: status codes, body shape, upstream failures.

Every error is a FHIR OperationOutcome (application/fhir+json), as FHIR/SDC
clients expect — not FastAPI's {"detail": ...}.
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _issue(response) -> dict:
    assert response.headers["content-type"].startswith("application/fhir+json")
    body = response.json()
    assert body["resourceType"] == "OperationOutcome", body
    return body["issue"][0]


async def test_wrong_resource_type_returns_400(api_client):
    response = await api_client.post("/api/questionnaires/", json={"resourceType": "Patient"})
    assert response.status_code == 400
    assert "Questionnaire" in _issue(response)["diagnostics"]


@pytest.mark.sdc_compliance
async def test_error_body_is_operation_outcome(api_client):
    response = await api_client.post("/api/questionnaires/", json={"resourceType": "Patient"})
    assert response.status_code == 400
    issue = _issue(response)
    assert issue["severity"] == "error"
    assert issue["code"] == "invalid"


async def test_not_found_is_operation_outcome(api_client):
    response = await api_client.get("/api/questionnaires/does-not-exist-xyz/$package")
    assert response.status_code == 404
    assert _issue(response)["code"] == "not-found"


async def test_unknown_route_is_operation_outcome(api_client):
    response = await api_client.get("/api/no-such-route")
    assert response.status_code == 404
    assert _issue(response)["code"] == "not-found"


async def test_malformed_json_returns_422(api_client):
    response = await api_client.post(
        "/api/questionnaires/",
        content=b'{"resourceType": "Questionnaire", invalid json}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422  # FastAPI request validation
    issue = _issue(response)
    assert issue["code"] == "structure"
    assert issue["expression"]


async def test_hapi_failure_surfaces_as_500(api_client, sidecar_app):
    """When the FHIR client raises (HAPI down, network error), the sidecar
    answers 500 with an OperationOutcome instead of hanging."""
    if sidecar_app is None:
        pytest.skip("dependency override needs the in-process app (unset API_BASE_URL)")
    from app.services.fhir_client import get_fhir_client

    class _Broken:
        async def get_resource(self, *_args, **_kwargs):
            raise ConnectionError("simulated: HAPI unreachable")

    sidecar_app.dependency_overrides[get_fhir_client] = lambda: _Broken()

    response = await api_client.get("/api/questionnaires/any-id")

    assert response.status_code == 500
    issue = _issue(response)
    assert issue["code"] == "exception"
    assert "HAPI unreachable" in issue["diagnostics"]


async def test_unknown_query_parameters_are_ignored(api_client):
    response = await api_client.get("/api/questionnaires/search", params={"invalid_unknown_param": "value"})
    assert response.status_code == 200
    assert response.json()["resourceType"] == "Bundle"


async def test_health_reports_version_and_fhir_target(api_client):
    response = await api_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["fhir_base_url"].endswith("/fhir")
    assert body["version"]
