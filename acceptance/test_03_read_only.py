"""3 Read-only: no writes, no system operations, no patient data.

Each probe is harmless even if the rule were broken: bodies are invalid for
the target, ids do not exist, system operations are read-only ones.
"""
import pytest

from conftest import FHIR_JSON, outcome_code

pytestmark = pytest.mark.readonly

NOPE = "acceptance-probe-does-not-exist"
JSON = {"Content-Type": FHIR_JSON}

WRITES = [
    ("POST", "/Questionnaire", {"resourceType": "Patient"}),          # type mismatch: HAPI would 400
    ("PUT", f"/Questionnaire/{NOPE}", {"resourceType": "Basic"}),     # type mismatch: HAPI would 400
    ("DELETE", f"/Questionnaire/{NOPE}", None),                         # nothing to delete
    ("DELETE", "/Questionnaire?url=https://acceptance.invalid/none", None),  # conditional, matches nothing
    ("POST", "/", {"resourceType": "Bundle", "type": "batch", "entry": []}),  # empty batch
    ("PATCH", f"/Questionnaire/{NOPE}", []),
]


@pytest.mark.parametrize("method,path,body", WRITES, ids=[f"{m} {p}" for m, p, _ in WRITES])
def test_writes_are_refused(base, client, method, path, body):
    r = client.request(method, f"{base}{path}", json=body, headers=JSON)
    assert r.status_code == 405, f"{method} {path}: {r.status_code} {r.text[:200]}"
    assert outcome_code(r) == "not-supported"


BLOCKED = [
    ("GET", "/$meta"),                                        # system-level operation (read-only one)
    ("GET", "/%24meta"),                                      # same, URL-encoded
    ("POST", f"/Questionnaire/{NOPE}/$expunge"),
    ("GET", f"/Questionnaire/{NOPE}/$populate"),
    ("POST", "/QuestionnaireResponse/$extract"),
    ("POST", f"/Questionnaire/{NOPE}/$compute-and-extract"),
    ("GET", "/QuestionnaireResponse?_count=0"),
    ("GET", "/Observation?_count=0"),
    ("GET", "/Patient?_count=0"),
    ("GET", "/swagger-ui/"),
    ("GET", "/api-docs"),
]


@pytest.mark.parametrize("method,path", BLOCKED, ids=[f"{m} {p}" for m, p in BLOCKED])
def test_system_ops_and_patient_data_are_blocked(base, client, method, path):
    r = client.request(method, f"{base}{path}", headers=JSON)
    assert r.status_code == 403, f"{method} {path}: {r.status_code} {r.text[:200]}"
    assert outcome_code(r) == "forbidden"


def test_encoded_query_in_an_id_does_not_reach_other_routes(base, client):
    r = client.get(f"{base}/Questionnaire/x%3Fq%3D1/$package")
    assert r.status_code != 200 or r.json().get("resourceType") != "Bundle", r.text[:200]
