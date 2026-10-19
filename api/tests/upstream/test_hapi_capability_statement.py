"""HAPI's CapabilityStatement — what the Form Manager image advertises.

These are tests of HAPI, kept because clients discover SDC operations here.
The sidecar itself has no CapabilityStatement (open bead).
"""
import pytest

pytestmark = [pytest.mark.upstream, pytest.mark.sdc_compliance, pytest.mark.asyncio]


@pytest.fixture(scope="module")
def capability(fhir_base_url, _hapi_ready):
    import httpx
    return httpx.get(f"{fhir_base_url}/metadata", timeout=30.0, headers={"Cache-Control": "no-cache"}).json()


@pytest.fixture(scope="module")
def questionnaire_rest(capability):
    for rest in capability["rest"]:
        for resource in rest.get("resource", []):
            if resource["type"] == "Questionnaire":
                return resource
    pytest.fail("Questionnaire not declared in CapabilityStatement.rest.resource")


def test_capability_statement_required_fields(capability):
    assert capability["resourceType"] == "CapabilityStatement"
    assert capability["status"] in ("draft", "active", "retired")
    for field in ("date", "kind", "fhirVersion", "format"):
        assert field in capability
    assert "json" in capability["format"] or "application/fhir+json" in capability["format"]


def test_declares_fhir_r4(capability):
    assert capability["fhirVersion"].startswith("4.0"), capability["fhirVersion"]


def test_questionnaire_interactions(questionnaire_rest):
    """SDC Form Manager SHALL support read and search-type."""
    codes = {i["code"] for i in questionnaire_rest.get("interaction", [])}
    assert {"read", "search-type", "create", "update", "delete"} <= codes


def test_questionnaire_declares_sdc_operations(questionnaire_rest):
    """HAPI CR advertises $package and $populate on Questionnaire.
    (HAPI names operations without the `$`.)"""
    ops = {op["name"] for op in questionnaire_rest.get("operation", [])}
    assert {"package", "populate"} <= ops, f"operations advertised: {sorted(ops)}"


def test_questionnaire_declares_canonical_search_params(questionnaire_rest):
    names = {sp["name"] for sp in questionnaire_rest.get("searchParam", [])}
    assert {"url", "version", "status", "title", "_lastUpdated"} <= names


def test_no_sdc_form_manager_instantiates(capability):
    """Documents the gap: nothing declares conformance to the SDC Form
    Manager CapabilityStatement. Flip this test when the sidecar (or a
    custom HAPI CapabilityStatement) starts declaring it."""
    declared = [c for c in capability.get("instantiates", []) if "sdc" in c.lower()]
    assert declared == []
