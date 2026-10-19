"""2 Access: client certificate from a trusted CA, plus the site allowlist."""
import pytest

from conftest import outcome_code

pytestmark = pytest.mark.access


def test_no_client_certificate_is_rejected(base, anon_client):
    r = anon_client.get(f"{base}/metadata")
    assert r.status_code == 401, r.text[:200]
    assert outcome_code(r) == "login"


def test_untrusted_ca_is_rejected(base, rogue_client):
    r = rogue_client.get(f"{base}/metadata")
    assert r.status_code == 401, r.text[:200]
    assert outcome_code(r) == "login"


def test_trusted_but_not_allowlisted_is_forbidden(base, unlisted_client):
    r = unlisted_client.get(f"{base}/metadata")
    assert r.status_code == 403, r.text[:200]
    assert outcome_code(r) == "forbidden"


def test_forged_identity_header_does_not_bypass_the_allowlist(base, unlisted_client):
    r = unlisted_client.get(f"{base}/metadata", headers={"X-Client-Site": "anything"})
    assert r.status_code == 403


def test_allowlisted_client_reaches_the_fhir_base(base, client):
    r = client.get(f"{base}/metadata")
    assert r.status_code == 200
    assert r.json()["resourceType"] == "CapabilityStatement"


@pytest.mark.parametrize("path", ["/api/questionnaires/", "/actuator/health", "/docs", "/"])
def test_nothing_outside_the_fhir_base_is_served(endpoint, client, path):
    r = client.get(f"{endpoint}{path}")
    assert r.status_code == 404, f"{path}: {r.status_code}"
    assert outcome_code(r) == "not-found"
