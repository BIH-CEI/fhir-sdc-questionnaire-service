"""
PRO-CTCAE Scoring Service — ETL component for composite grading.

Takes a QuestionnaireResponse with raw answers, calls Library/$evaluate
on HAPI CR to compute CompositeGradeResult per symptom, and builds
FHIR Observations with valueInteger or dataAbsentReason.

Architecture (Spike April 2026):
  - $extract and $populate do NOT evaluate calculatedExpression
  - Library/$evaluate with CQL parameters is the server-side scoring path
  - This service wraps that into a single QR-in → Observations-out call
"""

import httpx
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# PRO-CTCAE CQL Library canonical URL and ID
CQL_LIBRARY_ID = "PRO_CTCAE"
CQL_LIBRARY_URL = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Library/mii-lib-pro-ctcae"

# Mapping: linkId suffix → CQL parameter name
ATTR_TO_PARAM = {
    "frq": "frq",
    "sev": "sev",
    "int": "intrf",  # 'int' is reserved in CQL
    "yn": None,       # binary items don't go through composite grading
}

# Opt-out code → CQL parameter mapping
OPTOUT_PARAMS = {
    "proctcae-optout-not-applicable": "optOutNotApplicable",
    "proctcae-optout-not-sexually-active": "optOutNotSexuallyActive",
    "proctcae-optout-prefer-not-to-answer": "optOutPreferNotToAnswer",
}

# dataAbsentReason system
DAR_SYSTEM = "http://terminology.hl7.org/CodeSystem/data-absent-reason"

# Score catalogue codes
COMPOSITE_GRADE_CODE = "proctcae-composite-grade"
ACS_CODE = "proctcae-acs"
SCORE_CATALOGUE_SYSTEM = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/CodeSystem/mii-cs-pro-score-catalogue"
PROCTCAE_CS = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/CodeSystem/mii-cs-pro-pro-ctcae"


def _extract_symptom_groups(qr: dict) -> list[dict]:
    """
    Extract symptom groups from a QuestionnaireResponse.
    Each top-level group item (linkId like 'proctcae-53') is one symptom.
    Returns list of {ae_id, linkId, items: [{attr, value, optout_code}]}.
    """
    groups = []
    for item in qr.get("item", []):
        link_id = item.get("linkId", "")
        if not link_id.startswith("proctcae-"):
            continue

        # Extract AE number from group linkId (e.g., "proctcae-53" → "53")
        ae_id = link_id.replace("proctcae-", "")

        sub_items = []
        for sub in item.get("item", []):
            sub_link = sub.get("linkId", "")
            answers = sub.get("answer", [])
            if not answers:
                continue

            answer = answers[0]

            # Check for opt-out coding
            coding = answer.get("valueCoding", {})
            code = coding.get("code", "")
            if code in OPTOUT_PARAMS:
                sub_items.append({
                    "attr": None,
                    "value": None,
                    "optout_code": code,
                })
                continue

            # Extract ordinal value
            value = None
            # Check ordinalValue extension on the coding
            for ext in coding.get("extension", []):
                if ext.get("url", "").endswith("ordinalValue"):
                    value = int(ext.get("valueDecimal", 0))
                    break

            # Fallback: try valueInteger directly
            if value is None and "valueInteger" in answer:
                value = answer["valueInteger"]

            # Determine attribute from linkId suffix
            parts = sub_link.rsplit("-", 1)
            attr = parts[-1] if len(parts) > 1 else None

            sub_items.append({
                "attr": attr,
                "value": value,
                "optout_code": None,
            })

        groups.append({
            "ae_id": ae_id,
            "linkId": link_id,
            "items": sub_items,
        })

    return groups


def _build_evaluate_params(group: dict) -> dict:
    """Build CQL Library/$evaluate Parameters for one symptom group."""
    params = []

    # Check for opt-outs first
    for item in group["items"]:
        if item["optout_code"]:
            cql_param = OPTOUT_PARAMS[item["optout_code"]]
            params.append({"name": cql_param, "valueBoolean": True})

    # Add attribute values
    for item in group["items"]:
        if item["attr"] and item["value"] is not None:
            cql_name = ATTR_TO_PARAM.get(item["attr"])
            if cql_name:
                params.append({"name": cql_name, "valueInteger": item["value"]})

    return {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "subject",
                "valueString": "Patient/anonymous",
            },
            {
                "name": "parameters",
                "resource": {
                    "resourceType": "Parameters",
                    "parameter": params,
                },
            },
        ],
    }


def _build_observation(
    ae_id: str,
    ae_display: str,
    score: Optional[int],
    absent_reason: Optional[str],
    subject_ref: Optional[str] = None,
) -> dict:
    """Build a FHIR Observation for a composite grade."""
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "survey",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": SCORE_CATALOGUE_SYSTEM,
                    "code": COMPOSITE_GRADE_CODE,
                    "display": "PRO-CTCAE Composite Grade",
                },
                {
                    "system": PROCTCAE_CS,
                    "code": f"proctcae-ae-{ae_id}",
                    "display": ae_display,
                },
            ],
        },
    }

    if subject_ref:
        obs["subject"] = {"reference": subject_ref}

    if score is not None:
        obs["valueInteger"] = score
    elif absent_reason:
        obs["dataAbsentReason"] = {
            "coding": [
                {
                    "system": DAR_SYSTEM,
                    "code": absent_reason,
                }
            ]
        }

    return obs


def _build_acs_observation(
    acs_score: Optional[float],
    scored_count: int,
    excluded_count: int,
    subject_ref: Optional[str] = None,
) -> dict:
    """Build a FHIR Observation for the Average Composite Score."""
    obs = {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "survey",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": SCORE_CATALOGUE_SYSTEM,
                    "code": ACS_CODE,
                    "display": "PRO-CTCAE Average Composite Score (ACS)",
                }
            ],
        },
        "component": [
            {
                "code": {"text": "Scored symptom count"},
                "valueInteger": scored_count,
            },
            {
                "code": {"text": "Excluded symptom count"},
                "valueInteger": excluded_count,
            },
        ],
    }

    if subject_ref:
        obs["subject"] = {"reference": subject_ref}

    if acs_score is not None:
        obs["valueQuantity"] = {
            "value": round(acs_score, 2),
            "unit": "score",
            "system": "http://unitsofmeasure.org",
            "code": "{score}",
        }
    else:
        obs["dataAbsentReason"] = {
            "coding": [{"system": DAR_SYSTEM, "code": "not-performed"}]
        }

    return obs


async def score_questionnaire_response(
    qr: dict,
    hapi_base_url: Optional[str] = None,
    subject_ref: Optional[str] = None,
) -> dict:
    """
    Score a PRO-CTCAE QuestionnaireResponse.

    Args:
        qr: FHIR QuestionnaireResponse with raw answers
        hapi_base_url: Override HAPI base URL (default from settings)
        subject_ref: Patient reference for Observations

    Returns:
        FHIR Bundle (collection) with Observations:
        - One Observation per symptom (composite grade or dataAbsentReason)
        - One Observation for ACS (average composite score)
    """
    base_url = hapi_base_url or settings.fhir_base_url
    groups = _extract_symptom_groups(qr)

    if not groups:
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [],
        }

    observations = []
    composite_scores = []  # for ACS calculation

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        for group in groups:
            ae_id = group["ae_id"]
            ae_display = group["linkId"]

            # Binary presence items don't get composite grades
            has_only_yn = all(
                item["attr"] == "yn" for item in group["items"] if item["attr"]
            )
            if has_only_yn:
                # Presence items: just extract yes/no as observation
                for item in group["items"]:
                    if item["value"] is not None:
                        obs = _build_observation(
                            ae_id, ae_display,
                            score=item["value"],
                            absent_reason=None,
                            subject_ref=subject_ref,
                        )
                        observations.append(obs)
                continue

            # Build CQL parameters and call Library/$evaluate
            eval_params = _build_evaluate_params(group)

            try:
                resp = await client.post(
                    f"/Library/{CQL_LIBRARY_ID}/$evaluate",
                    json=eval_params,
                    headers={"Content-Type": "application/fhir+json"},
                )

                if resp.status_code != 200:
                    logger.warning(
                        f"Library/$evaluate failed for AE {ae_id}: "
                        f"{resp.status_code} {resp.text[:200]}"
                    )
                    continue

                result = resp.json()
                score = None
                absent_reason = None

                if result.get("resourceType") == "Parameters":
                    for param in result.get("parameter", []):
                        name = param.get("name", "")
                        if name == "CompositeGradeScore":
                            score = param.get("valueInteger")
                        elif name == "CompositeGradeAbsentReason":
                            absent_reason = param.get("valueString")

                obs = _build_observation(
                    ae_id, ae_display, score, absent_reason, subject_ref
                )
                observations.append(obs)
                composite_scores.append(score)

            except Exception as e:
                logger.error(f"Error scoring AE {ae_id}: {e}")
                continue

    # Calculate ACS
    scored = [s for s in composite_scores if s is not None]
    excluded = len(composite_scores) - len(scored)
    acs = sum(scored) / len(scored) if scored else None

    acs_obs = _build_acs_observation(acs, len(scored), excluded, subject_ref)
    observations.append(acs_obs)

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "entry": [
            {"resource": obs} for obs in observations
        ],
    }
