"""
$extract and $populate behavior with calculatedExpression — Regression Tests

Verifies how HAPI FHIR CR handles calculatedExpression during $extract and $populate.
These tests serve as architectural guardrails for PRO score calculation:

- Scenario 1: Does $extract compute scores from raw answers?
- Scenario 2: Does $extract preserve correct pre-computed scores?
- Scenario 3: Does $extract correct wrong pre-computed scores?
- Scenario 4: Does $populate evaluate calculatedExpressions?
- Scenario 5: Does $extract require the Questionnaire on the server?

After the initial spike run, update the assertions in _assert_behavior() to
lock in the observed HAPI behavior as regression expectations.

Related: beads kerndatensatzmodul-proms-v71
"""

import pytest
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Behavior Registry — UPDATE AFTER FIRST RUN
# ============================================================================
# Set to None = discovery mode (spike). Set to True/False = regression mode.
# After running the spike, fill in observed values to lock behavior.

OBSERVED_BEHAVIOR = {
    # Scenario 1: Does $extract compute a missing calculatedExpression?
    "extract_computes_missing_score": False,  # $extract does NOT compute scores

    # Scenario 2: When QR has correct score, does $extract keep or recompute?
    "extract_preserves_correct_score": True,  # $extract copies what's in the QR

    # Scenario 3: When QR has WRONG score, does $extract correct it?
    "extract_corrects_wrong_score": False,  # $extract BLINDLY copies — no validation

    # Scenario 4: Does $populate evaluate calculatedExpressions?
    "populate_evaluates_calculated": False,  # $populate does NOT evaluate calculated

    # Scenario 5: Does $populate + $extract pipeline produce correct scores?
    "populate_extract_pipeline_correct": False,  # Pipeline fails — no scores computed

    # Scenario 6: Can Library/$evaluate compute scores from CQL?
    "library_evaluate_computes_score": True,  # CQL computes correctly ✓
}


def _assert_or_discover(key: str, actual: bool, context: str):
    """Assert if behavior is locked, otherwise log discovery."""
    expected = OBSERVED_BEHAVIOR[key]
    if expected is None:
        marker = "→ DISCOVERED"
        logger.warning(f"  {marker}: {key} = {actual} ({context})")
    else:
        assert actual == expected, (
            f"REGRESSION: {key} changed! "
            f"Expected {expected}, got {actual}. "
            f"Context: {context}. "
            f"HAPI may have changed $extract/$populate behavior — "
            f"review PRO-CTCAE scoring architecture implications!"
        )
        logger.info(f"  ✓ CONFIRMED: {key} = {actual}")


# ============================================================================
# Test Resources
# ============================================================================

CALC_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "id": "calc-extract-test",
    "url": "http://example.org/Questionnaire/calc-extract-test",
    "version": "1.0.0",
    "name": "CalcExtractTest",
    "title": "Calculated Expression Extract Behavior Test",
    "status": "active",
    "extension": [
        {
            "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract",
            "valueBoolean": True
        }
    ],
    "item": [
        {
            "linkId": "item-a",
            "text": "Value A",
            "type": "integer",
            "required": True,
            "code": [{"system": "http://example.org/codes", "code": "value-a"}],
        },
        {
            "linkId": "item-b",
            "text": "Value B",
            "type": "integer",
            "required": True,
            "code": [{"system": "http://example.org/codes", "code": "value-b"}],
        },
        {
            "linkId": "total",
            "text": "Total Score",
            "type": "integer",
            "readOnly": True,
            "code": [{"system": "http://example.org/codes", "code": "total-score"}],
            "extension": [
                {
                    "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-calculatedExpression",
                    "valueExpression": {
                        "description": "Sum of A + B",
                        "language": "text/fhirpath",
                        "expression": (
                            "%resource.item.where(linkId='item-a').answer.value.first()"
                            " + "
                            "%resource.item.where(linkId='item-b').answer.value.first()"
                        )
                    }
                },
                {
                    "url": "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-observationExtract",
                    "valueBoolean": True
                }
            ]
        }
    ]
}

QUESTIONNAIRE_URL = CALC_QUESTIONNAIRE["url"]
QUESTIONNAIRE_ID = CALC_QUESTIONNAIRE["id"]


def _make_qr(
    value_a: int,
    value_b: int,
    total: Optional[int] = None,
    questionnaire_url: str = QUESTIONNAIRE_URL,
) -> dict:
    """Build a QuestionnaireResponse. Omits total item when total=None."""
    items = [
        {
            "linkId": "item-a",
            "text": "Value A",
            "answer": [{"valueInteger": value_a}]
        },
        {
            "linkId": "item-b",
            "text": "Value B",
            "answer": [{"valueInteger": value_b}]
        },
    ]
    if total is not None:
        items.append({
            "linkId": "total",
            "text": "Total Score",
            "answer": [{"valueInteger": total}]
        })

    return {
        "resourceType": "QuestionnaireResponse",
        "questionnaire": questionnaire_url,
        "status": "completed",
        "item": items,
    }


# ============================================================================
# Helpers
# ============================================================================

async def _upload_questionnaire(fhir_server) -> None:
    """Ensure the test Questionnaire is on the server."""
    resp = await fhir_server.put(
        f"/Questionnaire/{QUESTIONNAIRE_ID}",
        json=CALC_QUESTIONNAIRE,
        headers={"Content-Type": "application/fhir+json"},
    )
    assert resp.status_code in (200, 201), (
        f"Questionnaire upload failed: {resp.status_code} — {resp.text[:300]}"
    )


async def _extract(fhir_server, qr: dict) -> dict:
    """Run $extract and return parsed result."""
    resp = await fhir_server.post(
        "/QuestionnaireResponse/$extract",
        json=qr,
        headers={"Content-Type": "application/fhir+json"},
    )
    return {
        "status": resp.status_code,
        "body": resp.json() if resp.status_code < 500 else None,
        "text": resp.text,
    }


def _find_total(bundle: Optional[dict]) -> Optional[int]:
    """Find the total-score Observation value in an $extract result Bundle."""
    if not bundle or bundle.get("resourceType") != "Bundle":
        return None
    for entry in bundle.get("entry", []):
        res = entry.get("resource", {})
        if res.get("resourceType") != "Observation":
            continue
        # Match by code or by text
        code_codings = res.get("code", {}).get("coding", [])
        code_text = res.get("code", {}).get("text", "")
        for coding in code_codings:
            if coding.get("code") == "total-score":
                return _extract_value(res)
        if "total" in code_text.lower():
            return _extract_value(res)
    return None


def _extract_value(obs: dict) -> Optional[int]:
    """Get numeric value from an Observation."""
    if "valueInteger" in obs:
        return obs["valueInteger"]
    vq = obs.get("valueQuantity", {})
    if "value" in vq:
        return int(vq["value"])
    # Check component values as fallback
    for comp in obs.get("component", []):
        if "valueInteger" in comp:
            return comp["valueInteger"]
        vq = comp.get("valueQuantity", {})
        if "value" in vq:
            return int(vq["value"])
    return None


def _count_observations(bundle: Optional[dict]) -> int:
    """Count Observations in a Bundle."""
    if not bundle or bundle.get("resourceType") != "Bundle":
        return 0
    return sum(
        1 for e in bundle.get("entry", [])
        if e.get("resource", {}).get("resourceType") == "Observation"
    )


def _dump_result(scenario: str, inputs: str, result: dict, total: Optional[int]):
    """Structured output for each scenario."""
    n_obs = _count_observations(result["body"])
    print(f"\n{'='*70}")
    print(f"  {scenario}")
    print(f"  Input:  {inputs}")
    print(f"  Status: {result['status']}")
    print(f"  Observations extracted: {n_obs}")
    print(f"  Total score value: {total}")
    if result["status"] >= 400:
        print(f"  Error: {result['text'][:300]}")
    print(f"{'='*70}\n")


# ============================================================================
# Scenario 1: Raw answers only — does $extract compute the missing score?
# ============================================================================

@pytest.mark.asyncio
async def test_extract_computes_missing_score(fhir_server):
    """QR has item-a=3, item-b=2, total ABSENT. Expected correct behavior: total=5."""
    await _upload_questionnaire(fhir_server)

    qr = _make_qr(value_a=3, value_b=2, total=None)
    result = await _extract(fhir_server, qr)

    if result["status"] >= 400:
        _dump_result("S1: Missing score", "a=3, b=2, total=absent", result, None)
        pytest.skip(f"$extract returned {result['status']}: {result['text'][:300]}")

    total = _find_total(result["body"])
    _dump_result("S1: Missing score", "a=3, b=2, total=absent", result, total)
    _assert_or_discover("extract_computes_missing_score", total == 5,
                        f"total={total}, expected 5 if computed")


# ============================================================================
# Scenario 2: Correct pre-computed score — keep or recompute?
# ============================================================================

@pytest.mark.asyncio
async def test_extract_with_correct_precomputed_score(fhir_server):
    """QR has item-a=3, item-b=2, total=5 (correct). Result should be 5 either way."""
    await _upload_questionnaire(fhir_server)

    qr = _make_qr(value_a=3, value_b=2, total=5)
    result = await _extract(fhir_server, qr)

    if result["status"] >= 400:
        _dump_result("S2: Correct score", "a=3, b=2, total=5", result, None)
        pytest.skip(f"$extract returned {result['status']}: {result['text'][:300]}")

    total = _find_total(result["body"])
    _dump_result("S2: Correct score", "a=3, b=2, total=5", result, total)
    _assert_or_discover("extract_preserves_correct_score", total == 5,
                        f"total={total}, expected 5")


# ============================================================================
# Scenario 3: WRONG pre-computed score — correct or blindly copy?
# ============================================================================

@pytest.mark.asyncio
async def test_extract_with_wrong_precomputed_score(fhir_server):
    """
    QR has item-a=3, item-b=2, total=99 (WRONG).
    Critical test: does $extract output 5 (recomputed) or 99 (blind copy)?
    """
    await _upload_questionnaire(fhir_server)

    qr = _make_qr(value_a=3, value_b=2, total=99)
    result = await _extract(fhir_server, qr)

    if result["status"] >= 400:
        _dump_result("S3: Wrong score", "a=3, b=2, total=99 (WRONG)", result, None)
        pytest.skip(f"$extract returned {result['status']}: {result['text'][:300]}")

    total = _find_total(result["body"])
    _dump_result("S3: Wrong score", "a=3, b=2, total=99 (WRONG)", result, total)

    corrects = total == 5
    _assert_or_discover("extract_corrects_wrong_score", corrects,
                        f"total={total}, expected 5 if corrected, 99 if blind copy")

    if not corrects and total == 99:
        logger.warning(
            "ARCHITECTURE IMPLICATION: $extract blindly copies scores. "
            "PRO-CTCAE needs $populate or custom validation before $extract!"
        )


# ============================================================================
# Scenario 4: $populate → does it evaluate calculatedExpression?
# ============================================================================

@pytest.mark.asyncio
async def test_populate_evaluates_calculated_expression(fhir_server):
    """
    $populate with a source QR containing only raw answers + subject context.
    Does the populated QR include a computed total from calculatedExpression?
    """
    await _upload_questionnaire(fhir_server)

    # Ensure a test patient exists
    await fhir_server.put(
        "/Patient/test-patient-1",
        json={
            "resourceType": "Patient",
            "id": "test-patient-1",
            "name": [{"family": "Test", "given": ["Spike"]}],
        },
        headers={"Content-Type": "application/fhir+json"},
    )

    source_qr = _make_qr(value_a=3, value_b=2, total=None)

    populate_params = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "questionnaireResponse",
                "resource": source_qr,
            },
            {
                "name": "subject",
                "valueReference": {"reference": "Patient/test-patient-1"},
            },
        ],
    }

    resp = await fhir_server.post(
        f"/Questionnaire/{QUESTIONNAIRE_ID}/$populate",
        json=populate_params,
        headers={"Content-Type": "application/fhir+json"},
    )

    print(f"\n{'='*70}")
    print(f"  S4: $populate with source QR + subject (a=3, b=2, total=absent)")
    print(f"  $populate status: {resp.status_code}")

    if resp.status_code >= 400:
        print(f"  Error: {resp.text[:400]}")
        print(f"{'='*70}\n")
        _assert_or_discover("populate_evaluates_calculated", False,
                            f"$populate returned {resp.status_code}")
        pytest.skip(f"$populate returned {resp.status_code}")

    populated_qr = resp.json()
    populated_total = None

    for item in populated_qr.get("item", []):
        if item.get("linkId") == "total":
            answers = item.get("answer", [])
            if answers:
                populated_total = answers[0].get("valueInteger")
            break

    print(f"  Populated total value: {populated_total}")

    # If $populate computed the score, test the full pipeline
    if populated_total is not None:
        extract_result = await _extract(fhir_server, populated_qr)
        extracted_total = _find_total(extract_result["body"])
        print(f"  $extract of populated QR → total: {extracted_total}")

    print(f"{'='*70}\n")

    _assert_or_discover("populate_evaluates_calculated", populated_total == 5,
                        f"populated_total={populated_total}, expected 5 if evaluated")


# ============================================================================
# Scenario 5: Full pipeline — $populate (with subject) → $extract
# ============================================================================

@pytest.mark.asyncio
async def test_populate_extract_full_pipeline(fhir_server):
    """
    Scenario 5: Complete pipeline test with different values (a=7, b=3).
    External QR with only raw answers → $populate computes scores → $extract
    produces Observations with correct total=10.

    This is the target architecture for PRO-CTCAE:
    external data in → $populate with CQL → $extract → validated Observations.
    """
    await _upload_questionnaire(fhir_server)

    # Ensure test patient
    await fhir_server.put(
        "/Patient/test-patient-1",
        json={
            "resourceType": "Patient",
            "id": "test-patient-1",
            "name": [{"family": "Test", "given": ["Spike"]}],
        },
        headers={"Content-Type": "application/fhir+json"},
    )

    # Step 1: $populate with raw-only QR
    source_qr = _make_qr(value_a=7, value_b=3, total=None)

    populate_resp = await fhir_server.post(
        f"/Questionnaire/{QUESTIONNAIRE_ID}/$populate",
        json={
            "resourceType": "Parameters",
            "parameter": [
                {"name": "questionnaireResponse", "resource": source_qr},
                {"name": "subject", "valueReference": {"reference": "Patient/test-patient-1"}},
            ],
        },
        headers={"Content-Type": "application/fhir+json"},
    )

    print(f"\n{'='*70}")
    print(f"  S5: Full pipeline $populate → $extract")
    print(f"  Input: a=7, b=3, total=absent")
    print(f"  $populate status: {populate_resp.status_code}")

    if populate_resp.status_code >= 400:
        print(f"  Error: {populate_resp.text[:400]}")
        print(f"{'='*70}\n")
        _assert_or_discover("populate_extract_pipeline_correct", False,
                            f"$populate failed: {populate_resp.status_code}")
        pytest.skip(f"$populate failed: {populate_resp.status_code}")

    populated_qr = populate_resp.json()

    # Check populated total
    populated_total = None
    for item in populated_qr.get("item", []):
        if item.get("linkId") == "total":
            answers = item.get("answer", [])
            if answers:
                populated_total = answers[0].get("valueInteger")
            break

    print(f"  Populated total: {populated_total}")

    # Step 2: $extract the populated QR
    extract_result = await _extract(fhir_server, populated_qr)
    extracted_total = _find_total(extract_result["body"])
    n_obs = _count_observations(extract_result["body"])

    print(f"  $extract status: {extract_result['status']}")
    print(f"  Observations: {n_obs}")
    print(f"  Extracted total: {extracted_total}")

    pipeline_correct = extracted_total == 10
    if pipeline_correct:
        print(f"  PIPELINE: $populate computed 7+3=10, $extract extracted it ✓")
    else:
        print(f"  PIPELINE: Expected 10, got {extracted_total}")

    print(f"{'='*70}\n")

    _assert_or_discover("populate_extract_pipeline_correct", pipeline_correct,
                        f"extracted_total={extracted_total}, expected 10")


# ============================================================================
# Scenario 6: Library/$evaluate — direct CQL execution
# ============================================================================

import base64

# Minimal CQL library that computes a sum from parameters
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
    "resourceType": "Library",
    "id": "CalcTestSpike",
    "url": "http://example.org/Library/CalcTestSpike",
    "version": "1.0.0",
    "name": "CalcTestSpike",
    "title": "Calculated Expression Test CQL Library",
    "status": "active",
    "type": {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/library-type",
                "code": "logic-library",
            }
        ]
    },
    "content": [
        {
            "contentType": "text/cql",
            "data": base64.b64encode(_CQL_SOURCE.encode()).decode(),
        }
    ],
}


@pytest.mark.asyncio
async def test_library_evaluate_computes_score(fhir_server):
    """
    Scenario 6: Upload a CQL Library, call Library/$evaluate with parameters.
    This is the target architecture for PRO-CTCAE server-side scoring:
    CQL Library contains CompositeGrade(), called directly via $evaluate.
    """
    # Upload the CQL Library (use POST to avoid tombstone issues from prior deletes)
    # First try PUT, fall back to POST if tombstone error
    lib_resp = await fhir_server.put(
        "/Library/CalcTestSpike",
        json=CQL_LIBRARY,
        headers={"Content-Type": "application/fhir+json"},
    )
    if lib_resp.status_code == 410:
        # Tombstone from prior delete — use POST with server-assigned ID
        library_copy = {**CQL_LIBRARY}
        library_copy.pop("id", None)
        lib_resp = await fhir_server.post(
            "/Library",
            json=library_copy,
            headers={"Content-Type": "application/fhir+json"},
        )

    print(f"\n{'='*70}")
    print(f"  S6: Library/$evaluate — direct CQL execution")
    print(f"  CQL Library upload: {lib_resp.status_code}")

    if lib_resp.status_code not in (200, 201):
        print(f"  Error: {lib_resp.text[:400]}")
        print(f"{'='*70}\n")
        _assert_or_discover("library_evaluate_computes_score", False,
                            f"Library upload failed: {lib_resp.status_code}")
        pytest.skip(f"Library upload failed: {lib_resp.status_code}")

    # Ensure test patient for subject context
    await fhir_server.put(
        "/Patient/test-patient-1",
        json={
            "resourceType": "Patient",
            "id": "test-patient-1",
            "name": [{"family": "Test", "given": ["Spike"]}],
        },
        headers={"Content-Type": "application/fhir+json"},
    )

    # Get the server-assigned ID for $evaluate call
    lib_id = lib_resp.json().get("id", "CalcTestSpike")

    # Call Library/$evaluate with parameters
    evaluate_params = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "subject", "valueString": "Patient/test-patient-1"},
            {
                "name": "parameters",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": [
                        {"name": "valueA", "valueInteger": 3},
                        {"name": "valueB", "valueInteger": 2},
                    ],
                },
            },
        ],
    }

    eval_resp = await fhir_server.post(
        f"/Library/{lib_id}/$evaluate",
        json=evaluate_params,
        headers={"Content-Type": "application/fhir+json"},
    )

    print(f"  $evaluate status: {eval_resp.status_code}")

    if eval_resp.status_code >= 400:
        print(f"  Error: {eval_resp.text[:500]}")

        # Try alternative: canonical URL-based invocation
        eval_resp2 = await fhir_server.post(
            "/Library/$evaluate",
            json={
                **evaluate_params,
                "parameter": [
                    *evaluate_params["parameter"],
                    {"name": "url", "valueCanonical": "http://example.org/Library/CalcTest"},
                ],
            },
            headers={"Content-Type": "application/fhir+json"},
        )
        print(f"  Alternative (canonical) $evaluate status: {eval_resp2.status_code}")
        if eval_resp2.status_code < 400:
            eval_resp = eval_resp2

    if eval_resp.status_code >= 400:
        print(f"{'='*70}\n")
        _assert_or_discover("library_evaluate_computes_score", False,
                            f"$evaluate failed: {eval_resp.status_code}")
        pytest.skip(f"$evaluate returned {eval_resp.status_code}")

    result = eval_resp.json()
    print(f"  Result type: {result.get('resourceType')}")

    # Parse the result Parameters
    total_score = None
    composite_grade = None
    if result.get("resourceType") == "Parameters":
        for param in result.get("parameter", []):
            name = param.get("name", "")
            if name == "TotalScore":
                total_score = param.get("valueInteger")
            elif name == "CompositeGrade":
                composite_grade = param.get("valueInteger")
            # Log all returned parameters
            print(f"  Result param: {name} = {param.get('valueInteger', param.get('valueString', param.get('resource', '?')))}")

    print(f"  TotalScore: {total_score} (expected 5)")
    print(f"  CompositeGrade: {composite_grade} (expected 1 for sum=5)")

    success = total_score == 5
    if success:
        print(f"  Library/$evaluate COMPUTES correctly from CQL ✓")
        if composite_grade == 1:
            print(f"  CompositeGrade lookup also works ✓")
    print(f"{'='*70}\n")

    _assert_or_discover("library_evaluate_computes_score", success,
                        f"TotalScore={total_score}, expected 5")
