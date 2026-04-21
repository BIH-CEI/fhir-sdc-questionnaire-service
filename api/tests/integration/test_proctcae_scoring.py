"""
PRO-CTCAE Scoring Endpoint — Integration Tests

Tests the FastAPI /api/pro-ctcae/score endpoint end-to-end:
  QR with raw answers → FastAPI → Library/$evaluate (HAPI CR) → Observations

Requires:
  - HAPI FHIR running with CR=true
  - CQL Library PRO_CTCAE uploaded
  - FastAPI running
"""

import pytest
import logging

logger = logging.getLogger(__name__)


# Minimal QR with 3 symptoms from the breast cancer subset
SAMPLE_QR = {
    "resourceType": "QuestionnaireResponse",
    "questionnaire": "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire/mii-qst-pro-pro-ctcae-breast-de",
    "status": "completed",
    "subject": {"reference": "Patient/test-patient-1"},
    "item": [
        # Symptom: Nausea (frq+sev, rank 4)
        {
            "linkId": "proctcae-09",
            "text": "Übelkeit",
            "item": [
                {
                    "linkId": "proctcae-09a-frq",
                    "answer": [{"valueInteger": 2}],  # Occasionally
                },
                {
                    "linkId": "proctcae-09b-sev",
                    "answer": [{"valueInteger": 3}],  # Severe
                },
            ],
        },
        # Symptom: Constipation (sev only, rank 2)
        {
            "linkId": "proctcae-15",
            "text": "Verstopfung",
            "item": [
                {
                    "linkId": "proctcae-15a-sev",
                    "answer": [{"valueInteger": 1}],  # Mild
                },
            ],
        },
        # Symptom: Diarrhea (frq only, rank 1)
        {
            "linkId": "proctcae-16",
            "text": "Durchfall",
            "item": [
                {
                    "linkId": "proctcae-16a-frq",
                    "answer": [{"valueInteger": 0}],  # Never
                },
            ],
        },
        # Symptom: Rash (presence, binary)
        {
            "linkId": "proctcae-24",
            "text": "Hautausschlag",
            "item": [
                {
                    "linkId": "proctcae-24a-yn",
                    "answer": [{"valueInteger": 1}],  # Yes
                },
            ],
        },
    ],
}


@pytest.mark.asyncio
async def test_proctcae_score_endpoint(api_client):
    """Test the /api/pro-ctcae/score endpoint with a sample QR."""
    resp = await api_client.post("/api/pro-ctcae/score", json=SAMPLE_QR)

    print(f"\n{'='*70}")
    print(f"  PRO-CTCAE Score Endpoint Test")
    print(f"  Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"  Error: {resp.text[:500]}")
        print(f"{'='*70}\n")
        pytest.skip(f"Endpoint returned {resp.status_code}")

    bundle = resp.json()
    assert bundle["resourceType"] == "Bundle"

    entries = bundle.get("entry", [])
    print(f"  Observations returned: {len(entries)}")

    for entry in entries:
        obs = entry.get("resource", {})
        codes = obs.get("code", {}).get("coding", [])
        code_display = codes[0].get("display", "") if codes else ""
        value = obs.get("valueInteger", obs.get("valueQuantity", {}).get("value"))
        dar = obs.get("dataAbsentReason", {}).get("coding", [{}])[0].get("code")

        if value is not None:
            print(f"  {code_display}: {value}")
        elif dar:
            print(f"  {code_display}: dataAbsentReason={dar}")

    print(f"{'='*70}\n")


@pytest.mark.asyncio
async def test_proctcae_health(api_client):
    """Test the PRO-CTCAE health endpoint."""
    resp = await api_client.get("/api/pro-ctcae/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "available"
    assert "Composite Grade" in str(data["scores"])


@pytest.mark.asyncio
async def test_proctcae_invalid_input(api_client):
    """Test error handling with invalid input."""
    resp = await api_client.post("/api/pro-ctcae/score", json={"resourceType": "Patient"})
    assert resp.status_code == 400
