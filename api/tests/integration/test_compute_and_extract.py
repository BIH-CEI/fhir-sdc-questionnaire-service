"""
$compute-and-extract — end-to-end integration tests for the sidecar
operation that bridges HAPI CR's gap (no auto-evaluation of
sdc-calculatedExpression during $populate / $extract).

Pipeline under test:
  POST /api/questionnaires/{id}/$compute-and-extract
    body: Parameters { subject: Reference(Patient/X) }

The sidecar:
  1. Reads the Questionnaire from HAPI
  2. Calls Library/$evaluate (cqf-library binding)
  3. Walks items flagged with observationExtract + calculatedExpression
  4. Builds Observations; looks up ObservationDefinition by item.code (LOINC)
     and uses qualifiedInterval bands for interpretation
  5. Persists as a transaction Bundle (or returns it if persist=false)

These tests assume the container ships:
  - bih-cei.fhir.pro-library 0.1.3 content (PHQ-9 + SF-4a Q+Library, ODs)
  - mii-pro 2026.3.0 (upstream ODs which our pro-library ODs co-exist with)
"""
import logging
import uuid
from typing import Optional

import pytest

logger = logging.getLogger(__name__)


# ─── PHQ-9 ordinals (per pro-library CQL OrdinalForCode) ─────────────────
PHQ9_ORDINAL_TO_LOINC = {
    0: "LA6568-5",  # Not at all
    1: "LA6569-3",  # Several days
    2: "LA6570-1",  # More than half the days
    3: "LA6571-9",  # Nearly every day
}

# Expected (raw → severity code, T-Score) per Kroenke 2001 + PROsetta Stone
# (Choi 2014). Mirrors the case tables in pro-library/input/cql/PHQ9.cql.
PHQ9_EXPECTATIONS = [
    # (raw, severity_code, tscore)
    ( 0, "minimal",            37.4),
    ( 4, "minimal",            50.5),
    ( 5, "mild",               52.5),
    ( 9, "mild",               58.6),
    (10, "moderate",           59.9),
    (14, "moderate",           64.7),
    (15, "moderately-severe",  65.8),
    (19, "moderately-severe",  70.3),
    (20, "severe",             71.5),
    (27, "severe",             82.3),
]

# ─── SF-4a ordinals (per pro-library CQL) ────────────────────────────────
SF4A_ORDINAL_TO_LOINC = {
    1: "LA6270-8",   # Never
    2: "LA10066-1",  # Rarely
    3: "LA10082-8",  # Sometimes
    4: "LA10044-8",  # Often
    5: "LA9933-8",   # Always
}

# (raw, tscore) per pro-library PROMISDepressionSF4a.cql lookup
SF4A_EXPECTATIONS = [
    ( 4, 41.0),  # all "Never"
    (12, 56.2),  # all "Sometimes"
    (20, 79.4),  # all "Always"
]


# ─── Canonicals ──────────────────────────────────────────────────────────
PHQ9_Q_ID = "phq-9"
SF4A_Q_ID = "promis-depression-sf4a"

LOINC_PHQ9_SUM   = "44261-6"
LOINC_PROMIS_T   = "77861-3"
LOINC_SF4A_RAW   = "77821-7"

CS_PHQ9_SEVERITY      = "https://fhir.bih-charite.de/pro-library/CodeSystem/phq-9-severity"
CS_PROMIS_T_SEVERITY  = "https://fhir.bih-charite.de/pro-library/CodeSystem/promis-depression-tscore-severity"


# ─── Helpers ─────────────────────────────────────────────────────────────

def _phq9_qr(patient_ref: str, raw: int) -> dict:
    """Build a PHQ-9 QuestionnaireResponse whose 9 scored items sum to `raw`."""
    assert 0 <= raw <= 27
    # Greedy decomposition: as many 3s as fit, one remainder, rest 0s.
    full_threes, remainder = divmod(raw, 3)
    ordinals = [3] * full_threes + ([remainder] if remainder else []) + [0] * 9
    ordinals = ordinals[:9]
    items = []
    for idx, ordinal in enumerate(ordinals, start=1):
        items.append({
            "linkId": f"phq-phq9-q{idx:02d}",
            "answer": [{"valueCoding": {
                "system": "http://loinc.org",
                "code": PHQ9_ORDINAL_TO_LOINC[ordinal],
            }}],
        })
    return {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": "https://fhir.bih-charite.de/pro-library/Questionnaire/phq-9|0.1.3",
        "status": "completed",
        "subject": {"reference": patient_ref},
        "authored": "2026-05-17T10:00:00Z",
        "item": items,
    }


def _sf4a_qr(patient_ref: str, ordinal_per_item: int) -> dict:
    """Build an SF-4a QR where every item has the same ordinal."""
    assert 1 <= ordinal_per_item <= 5
    return {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": "https://fhir.bih-charite.de/pro-library/Questionnaire/promis-depression-sf4a|0.1.3",
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


async def _create_patient(fhir_server) -> str:
    """Create a throwaway Patient. Returns 'Patient/<id>'."""
    r = await fhir_server.post(
        "/Patient",
        json={"resourceType": "Patient",
              "name": [{"family": f"Compute-{uuid.uuid4().hex[:6]}"}]},
        headers={"Content-Type": "application/fhir+json"},
    )
    r.raise_for_status()
    return f"Patient/{r.json()['id']}"


async def _post_qr(fhir_server, qr: dict) -> str:
    r = await fhir_server.post(
        "/QuestionnaireResponse", json=qr,
        headers={"Content-Type": "application/fhir+json"},
    )
    r.raise_for_status()
    return f"QuestionnaireResponse/{r.json()['id']}"


async def _compute_and_extract(api_client, q_id: str, patient_ref: str,
                               persist: bool = True) -> dict:
    r = await api_client.post(
        f"/api/questionnaires/{q_id}/$compute-and-extract",
        params={"persist": "true" if persist else "false"},
        json={"resourceType": "Parameters",
              "parameter": [{"name": "subject",
                             "valueReference": {"reference": patient_ref}}]},
        headers={"Content-Type": "application/fhir+json"},
    )
    return {"status": r.status_code, "body": r.json() if r.content else None,
            "text": r.text}


def _find_observation(bundle: dict, loinc: str) -> Optional[dict]:
    for entry in bundle.get("entry", []):
        obs = entry.get("resource", {})
        for c in obs.get("code", {}).get("coding", []):
            if c.get("code") == loinc:
                return obs
    return None


def _interpretation_code(obs: dict) -> Optional[str]:
    for interp in obs.get("interpretation", []):
        for c in interp.get("coding", []):
            return c.get("code")
    return None


# ─── Tests ───────────────────────────────────────────────────────────────

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.mark.parametrize("raw,severity,tscore", PHQ9_EXPECTATIONS)
async def test_phq9_compute_and_extract_boundary(
    fhir_server, api_client, raw, severity, tscore,
):
    """For each PHQ-9 boundary fixture: 2 Observations with correct
    value + OD-derived interpretation."""
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw))

    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"
    bundle = result["body"]
    assert bundle.get("resourceType") == "Bundle"

    sum_obs = _find_observation(bundle, LOINC_PHQ9_SUM)
    assert sum_obs is not None, f"no PHQ-9 sum Observation in bundle"
    assert sum_obs["valueQuantity"]["value"] == raw
    # PHQ-9 sum is integer — no false-precision dot
    assert isinstance(sum_obs["valueQuantity"]["value"], int)
    assert _interpretation_code(sum_obs) == severity, (
        f"raw={raw}: expected severity={severity}, "
        f"got {_interpretation_code(sum_obs)}"
    )
    # interpretation must come from our pro-library CodeSystem (not e.g. v3-ObservationInterpretation)
    coding_systems = {
        c.get("system")
        for interp in sum_obs.get("interpretation", [])
        for c in interp.get("coding", [])
    }
    assert CS_PHQ9_SEVERITY in coding_systems

    t_obs = _find_observation(bundle, LOINC_PROMIS_T)
    assert t_obs is not None, "no PROMIS T-Score Observation in bundle"
    assert t_obs["valueQuantity"]["value"] == pytest.approx(tscore, abs=0.01)


async def test_phq9_observation_has_derivedFrom_qr(fhir_server, api_client):
    """Each Observation must carry derivedFrom → the source QR (provenance)."""
    patient_ref = await _create_patient(fhir_server)
    qr_ref = await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=10))

    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref)
    assert result["status"] == 200
    for entry in result["body"].get("entry", []):
        df = entry["resource"].get("derivedFrom", [])
        assert any(d.get("reference") == qr_ref for d in df), (
            f"Observation missing derivedFrom={qr_ref}: {df}"
        )


async def test_phq9_category_is_survey(fhir_server, api_client):
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=5))
    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref)
    assert result["status"] == 200
    for entry in result["body"]["entry"]:
        codes = {c.get("code")
                 for cat in entry["resource"].get("category", [])
                 for c in cat.get("coding", [])}
        assert "survey" in codes


async def test_persist_false_returns_transaction_bundle(fhir_server, api_client):
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=7))
    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref,
                                        persist=False)
    assert result["status"] == 200
    bundle = result["body"]
    assert bundle["type"] == "transaction"
    # Entries lack an id (not persisted) but carry request.method=POST
    for entry in bundle["entry"]:
        assert entry["request"]["method"] == "POST"
        assert entry["request"]["url"] == "Observation"
        assert "id" not in entry["resource"]


async def test_no_qr_returns_observations_without_derivedFrom(fhir_server, api_client):
    """If no QR exists for the subject, $evaluate may still compute null/zero;
    the call should either succeed (no Observations because all defines are
    null) or return 422 — but must never 500."""
    patient_ref = await _create_patient(fhir_server)  # no QR posted
    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref)
    assert result["status"] in (200, 422), (
        f"unexpected {result['status']}: {result['text'][:300]}"
    )


async def test_unknown_questionnaire_returns_4xx(api_client):
    result = await _compute_and_extract(
        api_client, "does-not-exist-xyz", "Patient/missing",
    )
    assert 400 <= result["status"] < 500


@pytest.mark.parametrize("ordinal,raw,tscore", [
    (1,  4, 41.0),
    (3, 12, 62.2),
    (5, 20, 79.4),
])
async def test_sf4a_compute_and_extract(
    fhir_server, api_client, ordinal, raw, tscore,
):
    """SF-4a end-to-end: both raw and T-Score Observations produced."""
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _sf4a_qr(patient_ref, ordinal_per_item=ordinal))

    result = await _compute_and_extract(api_client, SF4A_Q_ID, patient_ref)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"
    bundle = result["body"]

    raw_obs = _find_observation(bundle, LOINC_SF4A_RAW)
    assert raw_obs is not None, "no SF-4a raw Observation"
    assert raw_obs["valueQuantity"]["value"] == raw

    t_obs = _find_observation(bundle, LOINC_PROMIS_T)
    assert t_obs is not None, "no PROMIS T-Score Observation"
    assert t_obs["valueQuantity"]["value"] == pytest.approx(tscore, abs=0.05)


async def test_sf4a_shares_tscore_obsdef_with_phq9(fhir_server, api_client):
    """The same `cei-obsdef-promis-depression-tscore` (LOINC 77861-3) must
    drive interpretation for both PHQ-9-derived and SF-4a-derived T-Scores
    — proves the shared-OD architecture."""
    patient_ref = await _create_patient(fhir_server)
    # SF-4a all-Always → raw=20 → T=79.4 → severe band
    await _post_qr(fhir_server, _sf4a_qr(patient_ref, ordinal_per_item=5))
    result = await _compute_and_extract(api_client, SF4A_Q_ID, patient_ref)
    assert result["status"] == 200
    t_obs = _find_observation(result["body"], LOINC_PROMIS_T)
    assert t_obs is not None
    assert _interpretation_code(t_obs) == "severe"
    systems = {c.get("system")
               for interp in t_obs.get("interpretation", [])
               for c in interp.get("coding", [])}
    assert CS_PROMIS_T_SEVERITY in systems
