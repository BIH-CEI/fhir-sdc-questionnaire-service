"""
PRO-CTCAE scoring endpoint — /api/pro-ctcae/score.

STATUS: the endpoint is dead content-wise. The service calls
Library/PRO_CTCAE/$evaluate, and no package in the image ships that Library
(MII PRO 2026.7.0 and 2027.0.0-ballot.1 contain zero Library resources; the
PRO Library ships phq-9-scoring and promis-depression-sf4a-scoring only).
Every symptom therefore falls into the "evaluate failed, continue" branch and
the endpoint answers a Bundle holding only an ACS Observation with
dataAbsentReason. The scoring test is a strict xfail until the CQL Library is
shipped or the router is removed (open bead).
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

SAMPLE_QR = {
    "resourceType": "QuestionnaireResponse",
    "questionnaire": "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire/mii-qst-pro-pro-ctcae-breast-de",
    "status": "completed",
    "subject": {"reference": "Patient/test-patient-1"},
    "item": [
        {"linkId": "proctcae-09", "text": "Übelkeit", "item": [            # frq 2 + sev 3 → grade 3
            {"linkId": "proctcae-09a-frq", "answer": [{"valueInteger": 2}]},
            {"linkId": "proctcae-09b-sev", "answer": [{"valueInteger": 3}]},
        ]},
        {"linkId": "proctcae-15", "text": "Verstopfung", "item": [         # sev only
            {"linkId": "proctcae-15a-sev", "answer": [{"valueInteger": 1}]},
        ]},
        {"linkId": "proctcae-16", "text": "Durchfall", "item": [           # frq only, never
            {"linkId": "proctcae-16a-frq", "answer": [{"valueInteger": 0}]},
        ]},
        {"linkId": "proctcae-24", "text": "Hautausschlag", "item": [       # presence item
            {"linkId": "proctcae-24a-yn", "answer": [{"valueInteger": 1}]},
        ]},
    ],
}


@pytest.mark.xfail(
    strict=True,
    reason="Library/PRO_CTCAE is not shipped by any package in the image, so no "
           "composite grade can be computed. Ship the CQL Library (pro-library) "
           "or remove the router — open bead.",
)
async def test_score_returns_composite_grades(api_client):
    response = await api_client.post("/api/pro-ctcae/score", json=SAMPLE_QR)
    assert response.status_code == 200
    bundle = response.json()

    by_ae = {}
    acs = None
    for entry in bundle["entry"]:
        obs = entry["resource"]
        codes = {c["code"] for c in obs["code"]["coding"]}
        if "proctcae-acs" in codes:
            acs = obs
        else:
            ae = next(c for c in codes if c.startswith("proctcae-ae-"))
            by_ae[ae] = obs

    assert by_ae["proctcae-ae-09"]["valueInteger"] == 3     # frq 2 + sev 3
    assert by_ae["proctcae-ae-16"]["valueInteger"] == 0     # never
    assert by_ae["proctcae-ae-24"]["valueInteger"] == 1     # presence yes/no passthrough
    assert "valueQuantity" in acs
    assert acs["component"][0]["valueInteger"] == 3         # scored symptoms


async def test_score_without_library_degrades_to_absent_acs(api_client):
    """Current behaviour, pinned so a silent change is noticed: no composite
    grades for the CQL-scored symptoms; the presence item (yes/no) passes
    through without CQL; the ACS carries dataAbsentReason=not-performed."""
    response = await api_client.post("/api/pro-ctcae/score", json=SAMPLE_QR)
    assert response.status_code == 200
    resources = [e["resource"] for e in response.json()["entry"]]
    assert len(resources) == 2
    codes = [{c["code"] for c in r["code"]["coding"]} for r in resources]
    presence = resources[[i for i, c in enumerate(codes) if "proctcae-ae-24" in c][0]]
    assert presence["valueInteger"] == 1
    acs = resources[[i for i, c in enumerate(codes) if "proctcae-acs" in c][0]]
    assert acs["dataAbsentReason"]["coding"][0]["code"] == "not-performed"


async def test_health(api_client):
    response = await api_client.get("/api/pro-ctcae/health")
    assert response.status_code == 200
    assert response.json()["status"] == "available"


async def test_wrong_resource_type_returns_400(api_client):
    response = await api_client.post("/api/pro-ctcae/score", json={"resourceType": "Patient"})
    assert response.status_code == 400
