"""
$compute-and-extract — sidecar operation bridging HAPI CR's gap (no
auto-evaluation of sdc-calculatedExpression during $populate / $extract).

Pipeline under test:
  POST /api/questionnaires/{id}/$compute-and-extract
    body: Parameters { subject: Reference(Patient/X) }

  1. read the Questionnaire from HAPI
  2. Library/$evaluate (cqf-library binding), only the needed defines
  3. items flagged observationExtract + calculatedExpression → Observations
  4. ObservationDefinition.qualifiedInterval by item.code → interpretation
  5. persist as transaction (or return it with persist=false)

Content: PRO Library (PHQ-9, PROMIS SF-4a + scoring Libraries + ODs) at the
version pinned in versions.env. Every test gets a throwaway Patient
(`test_subject`) whose QRs and Observations are deleted on teardown.
"""
import pytest

from tests.support.pro_library import (
    CS_PHQ9_SEVERITY,
    CS_PROMIS_T_SEVERITY,
    LOINC_PHQ9_SUM,
    LOINC_PROMIS_T,
    LOINC_SF4A_RAW,
    PHQ9_Q_ID,
    SF4A_Q_ID,
    compute_and_extract,
    find_observation,
    interpretation_code,
    phq9_qr,
    post_qr,
    sf4a_qr,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

# Expected (raw → severity code, T-Score) per Kroenke 2001 + PROsetta Stone
# (Choi 2014). Mirrors the case tables in pro-library/input/cql/PHQ9.cql.
PHQ9_EXPECTATIONS = [
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


@pytest.mark.parametrize("raw,severity,tscore", PHQ9_EXPECTATIONS)
async def test_phq9_boundaries(fhir_server, api_client, test_subject, raw, severity, tscore):
    """Per PHQ-9 boundary: sum + T-Score Observations with OD-derived interpretation."""
    await post_qr(fhir_server, phq9_qr(test_subject, raw))

    result = await compute_and_extract(api_client, PHQ9_Q_ID, test_subject)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"
    bundle = result["body"]
    assert bundle["resourceType"] == "Bundle"

    sum_obs = find_observation(bundle, LOINC_PHQ9_SUM)
    assert sum_obs is not None, "no PHQ-9 sum Observation in bundle"
    assert sum_obs["valueQuantity"]["value"] == raw
    assert isinstance(sum_obs["valueQuantity"]["value"], int)  # no false precision
    assert interpretation_code(sum_obs) == severity
    systems = {c.get("system") for i in sum_obs["interpretation"] for c in i.get("coding", [])}
    assert CS_PHQ9_SEVERITY in systems

    t_obs = find_observation(bundle, LOINC_PROMIS_T)
    assert t_obs is not None, "no PROMIS T-Score Observation in bundle"
    assert t_obs["valueQuantity"]["value"] == pytest.approx(tscore, abs=0.01)


async def test_observations_are_persisted_and_carry_provenance(fhir_server, api_client, test_subject):
    qr_ref = await post_qr(fhir_server, phq9_qr(test_subject, raw=10))

    result = await compute_and_extract(api_client, PHQ9_Q_ID, test_subject)
    assert result["status"] == 200

    entries = result["body"]["entry"]
    assert len(entries) == 2
    for entry in entries:
        obs = entry["resource"]
        assert obs["id"], "persisted Observation has no id — transaction response not merged"
        assert entry["fullUrl"] == f"Observation/{obs['id']}"
        assert any(d.get("reference") == qr_ref for d in obs.get("derivedFrom", []))
        assert {c["code"] for cat in obs["category"] for c in cat["coding"]} == {"survey"}
        assert obs["subject"]["reference"] == test_subject
        # Really on the server, not just echoed back.
        stored = await fhir_server.get(f"/Observation/{obs['id']}")
        assert stored.status_code == 200
        assert stored.json()["code"] == obs["code"]


async def test_persist_false_returns_transaction_bundle(fhir_server, api_client, test_subject):
    await post_qr(fhir_server, phq9_qr(test_subject, raw=7))

    result = await compute_and_extract(api_client, PHQ9_Q_ID, test_subject, persist=False)

    assert result["status"] == 200
    bundle = result["body"]
    assert bundle["type"] == "transaction"
    for entry in bundle["entry"]:
        assert entry["request"] == {"method": "POST", "url": "Observation"}
        assert "id" not in entry["resource"]
    stored = await fhir_server.get("/Observation", params={"subject": test_subject, "_summary": "count"})
    assert stored.json().get("total", 0) == 0


async def test_subject_without_qr_returns_422(api_client, test_subject):
    """All CQL defines evaluate to null → no Observation can be built → 422, never 500."""
    result = await compute_and_extract(api_client, PHQ9_Q_ID, test_subject)
    assert result["status"] == 422
    assert "No Observations" in result["body"]["detail"]


async def test_unknown_questionnaire_returns_404(api_client):
    result = await compute_and_extract(api_client, "does-not-exist-xyz", "Patient/missing")
    assert result["status"] == 404


async def test_missing_subject_returns_400(api_client):
    response = await api_client.post(
        f"/api/questionnaires/{PHQ9_Q_ID}/$compute-and-extract", json={"resourceType": "Parameters"}
    )
    assert response.status_code == 400


async def test_questionnaire_without_cqf_library_returns_422(api_client, clean_questionnaire, test_subject):
    q_id = await clean_questionnaire({
        "resourceType": "Questionnaire", "status": "active", "title": "No scoring library",
        "item": [{"linkId": "1", "type": "integer", "text": "Q"}],
    })
    result = await compute_and_extract(api_client, q_id, test_subject)
    assert result["status"] == 422
    assert "cqf-library" in result["body"]["detail"]


@pytest.mark.parametrize("ordinal,raw,tscore", [(1, 4, 41.0), (3, 12, 62.2), (5, 20, 79.4)])
async def test_sf4a(fhir_server, api_client, test_subject, ordinal, raw, tscore):
    await post_qr(fhir_server, sf4a_qr(test_subject, ordinal_per_item=ordinal))

    result = await compute_and_extract(api_client, SF4A_Q_ID, test_subject)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"
    bundle = result["body"]

    raw_obs = find_observation(bundle, LOINC_SF4A_RAW)
    assert raw_obs is not None
    assert raw_obs["valueQuantity"]["value"] == raw
    t_obs = find_observation(bundle, LOINC_PROMIS_T)
    assert t_obs is not None
    assert t_obs["valueQuantity"]["value"] == pytest.approx(tscore, abs=0.05)


async def test_sf4a_shares_tscore_obsdef_with_phq9(fhir_server, api_client, test_subject):
    """One ObservationDefinition (LOINC 77861-3) drives interpretation for both
    PHQ-9- and SF-4a-derived T-Scores — the shared-OD architecture."""
    await post_qr(fhir_server, sf4a_qr(test_subject, ordinal_per_item=5))  # raw 20 → T 79.4 → severe

    result = await compute_and_extract(api_client, SF4A_Q_ID, test_subject)
    assert result["status"] == 200
    t_obs = find_observation(result["body"], LOINC_PROMIS_T)
    assert interpretation_code(t_obs) == "severe"
    systems = {c.get("system") for i in t_obs["interpretation"] for c in i.get("coding", [])}
    assert CS_PROMIS_T_SEVERITY in systems
