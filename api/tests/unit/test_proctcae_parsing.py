"""PRO-CTCAE QR parsing and Observation shaping — pure functions."""
import pytest

from app.services.proctcae_scoring import (
    _build_acs_observation,
    _build_evaluate_params,
    _build_observation,
    _extract_symptom_groups,
)

pytestmark = pytest.mark.unit

ORDINAL_EXT = "http://hl7.org/fhir/StructureDefinition/ordinalValue"


def test_extract_groups_reads_ordinal_extension_and_valueInteger():
    qr = {"item": [
        {"linkId": "proctcae-09", "item": [
            {"linkId": "proctcae-09a-frq", "answer": [{"valueCoding": {
                "code": "x", "extension": [{"url": ORDINAL_EXT, "valueDecimal": 2.0}]}}]},
            {"linkId": "proctcae-09b-sev", "answer": [{"valueInteger": 3}]},
            {"linkId": "proctcae-09c-int", "answer": []},      # unanswered → dropped
        ]},
        {"linkId": "not-proctcae", "item": [{"linkId": "x", "answer": [{"valueInteger": 1}]}]},
    ]}
    groups = _extract_symptom_groups(qr)
    assert len(groups) == 1
    assert groups[0]["ae_id"] == "09"
    assert [(i["attr"], i["value"]) for i in groups[0]["items"]] == [("frq", 2), ("sev", 3)]


def test_extract_groups_marks_optout_answers():
    qr = {"item": [{"linkId": "proctcae-31", "item": [
        {"linkId": "proctcae-31a-frq",
         "answer": [{"valueCoding": {"code": "proctcae-optout-not-sexually-active"}}]},
    ]}]}
    item = _extract_symptom_groups(qr)[0]["items"][0]
    assert item["optout_code"] == "proctcae-optout-not-sexually-active"
    assert item["value"] is None


def test_build_evaluate_params_maps_int_to_intrf_and_optouts():
    group = {"ae_id": "09", "linkId": "proctcae-09", "items": [
        {"attr": "frq", "value": 2, "optout_code": None},
        {"attr": "int", "value": 1, "optout_code": None},
        {"attr": "yn", "value": 1, "optout_code": None},   # no CQL param
        {"attr": None, "value": None, "optout_code": "proctcae-optout-prefer-not-to-answer"},
    ]}
    params = _build_evaluate_params(group)
    inner = params["parameter"][1]["resource"]["parameter"]
    assert {"name": "optOutPreferNotToAnswer", "valueBoolean": True} in inner
    assert {"name": "frq", "valueInteger": 2} in inner
    assert {"name": "intrf", "valueInteger": 1} in inner
    assert not any(p["name"] == "yn" for p in inner)


def test_build_observation_score_vs_absent_reason():
    scored = _build_observation("09", "Nausea", score=2, absent_reason=None, subject_ref="Patient/p")
    assert scored["valueInteger"] == 2
    assert scored["subject"] == {"reference": "Patient/p"}
    assert any(c["code"] == "proctcae-ae-09" for c in scored["code"]["coding"])

    absent = _build_observation("31", "Sexual", score=None, absent_reason="not-applicable")
    assert "valueInteger" not in absent
    assert absent["dataAbsentReason"]["coding"][0]["code"] == "not-applicable"


def test_build_acs_observation_rounds_and_counts():
    obs = _build_acs_observation(1.6666, scored_count=3, excluded_count=1)
    assert obs["valueQuantity"]["value"] == 1.67
    assert obs["component"][0]["valueInteger"] == 3
    assert obs["component"][1]["valueInteger"] == 1

    empty = _build_acs_observation(None, 0, 0)
    assert empty["dataAbsentReason"]["coding"][0]["code"] == "not-performed"
