"""
HAPI CR: $extract / $populate do NOT evaluate sdc-calculatedExpression.

Architectural guardrails for PRO score calculation — the reason
$compute-and-extract exists in the sidecar. Each scenario pins observed HAPI
behaviour; a change (HAPI starts computing scores) fails the run so the
sidecar design can be revisited.

- S1: $extract does not compute a missing calculated item
- S2: $extract copies a correct pre-computed score
- S3: $extract copies a WRONG pre-computed score (no validation)
- S4: $populate does not evaluate calculatedExpression
- S5: $populate → $extract pipeline yields no score
- S6: Library/$evaluate does compute from CQL (the path the sidecar uses)

Related: beads kerndatensatzmodul-proms-v71
"""
import base64
from typing import Optional

import pytest

pytestmark = [pytest.mark.upstream, pytest.mark.asyncio]

CALC_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "id": "calc-extract-test",
    "url": "http://example.org/Questionnaire/calc-extract-test",
    "version": "1.0.0",
    "name": "CalcExtractTest",
    "title": "Calculated Expression Extract Behavior Test",
    "status": "active",
    "extension": [{
        "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract",
        "valueBoolean": True,
    }],
    "item": [
        {"linkId": "item-a", "text": "Value A", "type": "integer", "required": True,
         "code": [{"system": "http://example.org/codes", "code": "value-a"}]},
        {"linkId": "item-b", "text": "Value B", "type": "integer", "required": True,
         "code": [{"system": "http://example.org/codes", "code": "value-b"}]},
        {"linkId": "total", "text": "Total Score", "type": "integer", "readOnly": True,
         "code": [{"system": "http://example.org/codes", "code": "total-score"}],
         "extension": [
             {"url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
              "valueExpression": {
                  "description": "Sum of A + B", "language": "text/fhirpath",
                  "expression": "%resource.item.where(linkId='item-a').answer.value.first() + "
                                "%resource.item.where(linkId='item-b').answer.value.first()",
              }},
             {"url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract",
              "valueBoolean": True},
         ]},
    ],
}
QUESTIONNAIRE_ID = CALC_QUESTIONNAIRE["id"]
FHIR_JSON = {"Content-Type": "application/fhir+json"}

_CQL_SOURCE = """\
library CalcTestSpike version '1.0.0'

using FHIR version '4.0.1'

parameter valueA Integer
parameter valueB Integer

define TotalScore:
  valueA + valueB

define CompositeGrade:
  case
    when TotalScore <= 2 then 0
    when TotalScore <= 5 then 1
    when TotalScore <= 8 then 2
    else 3
  end
"""
CQL_LIBRARY = {
    "resourceType": "Library", "id": "CalcTestSpike",
    "url": "http://example.org/Library/CalcTestSpike", "version": "1.0.0",
    "name": "CalcTestSpike", "title": "Calculated Expression Test CQL Library", "status": "active",
    "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/library-type", "code": "logic-library"}]},
    "content": [{"contentType": "text/cql", "data": base64.b64encode(_CQL_SOURCE.encode()).decode()}],
}


def _qr(value_a: int, value_b: int, total: Optional[int] = None) -> dict:
    items = [
        {"linkId": "item-a", "text": "Value A", "answer": [{"valueInteger": value_a}]},
        {"linkId": "item-b", "text": "Value B", "answer": [{"valueInteger": value_b}]},
    ]
    if total is not None:
        items.append({"linkId": "total", "text": "Total Score", "answer": [{"valueInteger": total}]})
    return {"resourceType": "QuestionnaireResponse", "questionnaire": CALC_QUESTIONNAIRE["url"],
            "status": "completed", "item": items}


@pytest.fixture
async def calc_questionnaire(fhir_server):
    """Idempotent PUT by fixed id; shared by all scenarios."""
    r = await fhir_server.put(f"/Questionnaire/{QUESTIONNAIRE_ID}", json=CALC_QUESTIONNAIRE, headers=FHIR_JSON)
    assert r.status_code in (200, 201), r.text[:300]
    return QUESTIONNAIRE_ID


async def _extract(fhir_server, qr: dict) -> dict:
    r = await fhir_server.post("/QuestionnaireResponse/$extract", json=qr, headers=FHIR_JSON)
    assert r.status_code == 200, f"$extract {r.status_code}: {r.text[:300]}"
    return r.json()


async def _populate(fhir_server, subject: str, source_qr: dict) -> dict:
    r = await fhir_server.post(
        f"/Questionnaire/{QUESTIONNAIRE_ID}/$populate",
        json={"resourceType": "Parameters", "parameter": [
            {"name": "questionnaireResponse", "resource": source_qr},
            {"name": "subject", "valueReference": {"reference": subject}},
        ]},
        headers=FHIR_JSON,
    )
    assert r.status_code == 200, f"$populate {r.status_code}: {r.text[:300]}"
    return r.json()


def _value(obs: dict) -> Optional[int]:
    if "valueInteger" in obs:
        return obs["valueInteger"]
    if "value" in obs.get("valueQuantity", {}):
        return int(obs["valueQuantity"]["value"])
    return None


def _extracted_total(bundle: dict) -> Optional[int]:
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Observation":
            continue
        if any(c.get("code") == "total-score" for c in res.get("code", {}).get("coding", [])):
            return _value(res)
    return None


def _populated_total(qr: dict) -> Optional[int]:
    for item in qr.get("item", []):
        if item.get("linkId") == "total":
            answers = item.get("answer", [])
            return answers[0].get("valueInteger") if answers else None
    return None


async def test_s1_extract_does_not_compute_missing_score(fhir_server, calc_questionnaire):
    bundle = await _extract(fhir_server, _qr(3, 2, total=None))
    assert _extracted_total(bundle) is None, (
        "HAPI $extract now computes calculatedExpression — revisit $compute-and-extract"
    )


async def test_s2_extract_copies_correct_precomputed_score(fhir_server, calc_questionnaire):
    bundle = await _extract(fhir_server, _qr(3, 2, total=5))
    assert _extracted_total(bundle) == 5


async def test_s3_extract_copies_wrong_precomputed_score(fhir_server, calc_questionnaire):
    """No validation: 99 goes in, 99 comes out. Scores must be computed
    server-side (Library/$evaluate) before they are trusted."""
    bundle = await _extract(fhir_server, _qr(3, 2, total=99))
    assert _extracted_total(bundle) == 99


async def test_s4_populate_does_not_evaluate_calculated_expression(fhir_server, calc_questionnaire, test_subject):
    populated = await _populate(fhir_server, test_subject, _qr(3, 2))
    assert populated["resourceType"] == "QuestionnaireResponse"
    assert _populated_total(populated) is None, (
        "HAPI $populate now evaluates calculatedExpression — revisit $compute-and-extract"
    )


async def test_s5_populate_then_extract_yields_no_score(fhir_server, calc_questionnaire, test_subject):
    populated = await _populate(fhir_server, test_subject, _qr(7, 3))
    bundle = await _extract(fhir_server, populated)
    assert _extracted_total(bundle) is None


async def test_s6_library_evaluate_computes_from_cql(fhir_server, test_subject):
    """The path the sidecar relies on: CQL via Library/$evaluate works."""
    r = await fhir_server.put(f"/Library/{CQL_LIBRARY['id']}", json=CQL_LIBRARY, headers=FHIR_JSON)
    assert r.status_code in (200, 201), r.text[:300]

    r = await fhir_server.post(
        f"/Library/{CQL_LIBRARY['id']}/$evaluate",
        json={"resourceType": "Parameters", "parameter": [
            {"name": "subject", "valueString": test_subject},
            {"name": "parameters", "resource": {"resourceType": "Parameters", "parameter": [
                {"name": "valueA", "valueInteger": 3}, {"name": "valueB", "valueInteger": 2}]}},
        ]},
        headers=FHIR_JSON,
    )
    assert r.status_code == 200, f"$evaluate {r.status_code}: {r.text[:300]}"
    named = {p.get("name"): p for p in r.json().get("parameter", [])}
    assert named["TotalScore"]["valueInteger"] == 5
    assert named["CompositeGrade"]["valueInteger"] == 1
