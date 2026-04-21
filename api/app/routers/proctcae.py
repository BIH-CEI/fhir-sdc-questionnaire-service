"""
PRO-CTCAE Scoring Router — ETL endpoint for composite grading.

POST /api/pro-ctcae/score
  Body: QuestionnaireResponse (raw answers)
  Returns: Bundle with Observations (composite grades + ACS)
"""

from fastapi import APIRouter, HTTPException
from app.services.proctcae_scoring import score_questionnaire_response
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pro-ctcae", tags=["PRO-CTCAE Scoring"])


@router.post("/score")
async def score_proctcae(qr: dict):
    """
    Score a PRO-CTCAE QuestionnaireResponse.

    Takes a QuestionnaireResponse with raw patient answers and returns
    a Bundle of Observations with computed composite grades (0-3) per
    symptom and an Average Composite Score (ACS).

    Symptoms with opt-out answers (Not applicable, Not sexually active,
    Prefer not to answer) receive Observations with dataAbsentReason
    instead of a numeric score.

    The scoring uses the NCI Composite Grading Algorithm (Basch et al., 2021)
    implemented as a CQL Library evaluated via HAPI FHIR CR Library/$evaluate.
    """
    if qr.get("resourceType") != "QuestionnaireResponse":
        raise HTTPException(
            status_code=400,
            detail="Expected a FHIR QuestionnaireResponse resource"
        )

    # Extract subject reference if present
    subject_ref = None
    subject = qr.get("subject", {})
    if isinstance(subject, dict):
        subject_ref = subject.get("reference")

    try:
        bundle = await score_questionnaire_response(
            qr=qr,
            subject_ref=subject_ref,
        )
        return bundle
    except Exception as e:
        logger.error(f"PRO-CTCAE scoring failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Scoring failed: {str(e)}"
        )


@router.get("/health")
async def proctcae_health():
    """Health check for PRO-CTCAE scoring service."""
    return {
        "status": "available",
        "service": "PRO-CTCAE Scoring",
        "cql_library": "PRO_CTCAE v1.0.0",
        "algorithm": "NCI Composite Grading (Basch et al., 2021)",
        "scores": ["Composite Grade (0-3)", "Average Composite Score (0.0-3.0)"],
    }
