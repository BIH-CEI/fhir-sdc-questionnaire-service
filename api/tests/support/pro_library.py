"""Builders and lookups for PRO Library content (PHQ-9, PROMIS SF-4a).

The QuestionnaireResponses pin the PRO Library version from versions.env
(via conftest) — never a literal.
"""
from typing import Optional

from tests.conftest import PRO_LIBRARY_CANONICALS, PRO_LIBRARY_VERSION

PHQ9_Q_ID = "phq-9"
SF4A_Q_ID = "promis-depression-sf4a"
PHQ9_SCORING_LIBRARY_ID = "phq-9-scoring"

LOINC_PHQ9_SUM = "44261-6"
LOINC_PROMIS_T = "77861-3"
LOINC_SF4A_RAW = "77821-7"

CS_PHQ9_SEVERITY = "https://fhir.bih-charite.de/pro-library/CodeSystem/phq-9-severity"
CS_PROMIS_T_SEVERITY = "https://fhir.bih-charite.de/pro-library/CodeSystem/promis-depression-tscore-severity"

# PHQ-9 ordinals (per pro-library CQL OrdinalForCode)
PHQ9_ORDINAL_TO_LOINC = {
    0: "LA6568-5",  # Not at all
    1: "LA6569-3",  # Several days
    2: "LA6570-1",  # More than half the days
    3: "LA6571-9",  # Nearly every day
}

# SF-4a ordinals (per pro-library CQL)
SF4A_ORDINAL_TO_LOINC = {
    1: "LA6270-8",   # Never
    2: "LA10066-1",  # Rarely
    3: "LA10082-8",  # Sometimes
    4: "LA10044-8",  # Often
    5: "LA9933-8",   # Always
}


def phq9_qr(patient_ref: str, raw: int) -> dict:
    """Build a PHQ-9 QuestionnaireResponse whose 9 scored items sum to `raw`."""
    assert 0 <= raw <= 27
    # Greedy decomposition: as many 3s as fit, one remainder, rest 0s.
    full_threes, remainder = divmod(raw, 3)
    ordinals = [3] * full_threes + ([remainder] if remainder else []) + [0] * 9
    ordinals = ordinals[:9]
    items = [
        {
            "linkId": f"phq-phq9-q{idx:02d}",
            "answer": [{"valueCoding": {
                "system": "http://loinc.org",
                "code": PHQ9_ORDINAL_TO_LOINC[ordinal],
            }}],
        }
        for idx, ordinal in enumerate(ordinals, start=1)
    ]
    return {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": f"{PRO_LIBRARY_CANONICALS['phq_9']}|{PRO_LIBRARY_VERSION}",
        "status": "completed",
        "subject": {"reference": patient_ref},
        "authored": "2026-05-17T10:00:00Z",
        "item": items,
    }


def sf4a_qr(patient_ref: str, ordinal_per_item: int) -> dict:
    """Build an SF-4a QR where every item has the same ordinal."""
    assert 1 <= ordinal_per_item <= 5
    return {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": f"{PRO_LIBRARY_CANONICALS['sf4a']}|{PRO_LIBRARY_VERSION}",
        "status": "completed",
        "subject": {"reference": patient_ref},
        "authored": "2026-05-17T10:00:00Z",
        "item": [
            {"linkId": linkid, "answer": [{"valueCoding": {
                "system": "http://loinc.org",
                "code": SF4A_ORDINAL_TO_LOINC[ordinal_per_item],
            }}]}
            for linkid in ("promis-eddep04", "promis-eddep06",
                           "promis-eddep29", "promis-eddep41")
        ],
    }


async def post_qr(fhir_server, qr: dict) -> str:
    r = await fhir_server.post(
        "/QuestionnaireResponse", json=qr,
        headers={"Content-Type": "application/fhir+json"},
    )
    r.raise_for_status()
    return f"QuestionnaireResponse/{r.json()['id']}"


async def compute_and_extract(api_client, q_id: str, patient_ref: str,
                              persist: bool = True) -> dict:
    r = await api_client.post(
        f"/api/questionnaires/{q_id}/$compute-and-extract",
        params={"persist": "true" if persist else "false"},
        json={"resourceType": "Parameters",
              "parameter": [{"name": "subject",
                             "valueReference": {"reference": patient_ref}}]},
    )
    return {"status": r.status_code, "body": r.json() if r.content else None,
            "text": r.text}


def find_observation(bundle: dict, loinc: str) -> Optional[dict]:
    for entry in bundle.get("entry", []):
        obs = entry.get("resource", {})
        for c in obs.get("code", {}).get("coding", []):
            if c.get("code") == loinc:
                return obs
    return None


def interpretation_code(obs: dict) -> Optional[str]:
    for interp in obs.get("interpretation", []):
        for c in interp.get("coding", []):
            return c.get("code")
    return None
