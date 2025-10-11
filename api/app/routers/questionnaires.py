"""Questionnaire API endpoints."""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List
from app.services import get_fhir_client, FHIRClientService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/questionnaires",
    tags=["questionnaires"],
)


@router.get("/search")
async def search_questionnaires(
    q: Optional[str] = Query(None, description="Search text for title/name"),
    status: Optional[str] = Query(None, description="Publication status (draft, active, retired)"),
    title: Optional[str] = Query(None, description="Questionnaire title"),
    _summary: bool = Query(False, description="Return summary only"),
    _count: int = Query(20, description="Number of results"),
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """
    Search for Questionnaires with autocomplete support.

    Examples:
        - GET /api/questionnaires/search?q=diabetes
        - GET /api/questionnaires/search?status=active
        - GET /api/questionnaires/search?title=patient
    """
    try:
        search_params = {}

        if q:
            # Text search across title and name
            search_params["_content"] = q
        if status:
            search_params["status"] = status
        if title:
            search_params["title:contains"] = title
        if _summary:
            search_params["_summary"] = "true"

        search_params["_count"] = _count

        resources = await fhir_client.search_resources("Questionnaire", **search_params)

        # Convert to JSON-serializable format
        results = [r.serialize() for r in resources]

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(results),
            "entry": [{"resource": r} for r in results]
        }

    except Exception as e:
        logger.error(f"Error searching questionnaires: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{questionnaire_id}")
async def get_questionnaire(
    questionnaire_id: str,
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """Get a specific Questionnaire by ID."""
    try:
        resource = await fhir_client.get_resource("Questionnaire", questionnaire_id)

        if not resource:
            raise HTTPException(
                status_code=404,
                detail=f"Questionnaire/{questionnaire_id} not found"
            )

        return resource.serialize()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_questionnaire(
    questionnaire: dict,
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """
    Create a new Questionnaire.

    Request body should be a FHIR Questionnaire resource in JSON format.
    """
    try:
        # Validate resource type
        if questionnaire.get("resourceType") != "Questionnaire":
            raise HTTPException(
                status_code=400,
                detail="Resource must be of type 'Questionnaire'"
            )

        resource = await fhir_client.create_resource("Questionnaire", questionnaire)

        return resource.serialize()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating questionnaire: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{questionnaire_id}")
async def update_questionnaire(
    questionnaire_id: str,
    questionnaire: dict,
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """Update an existing Questionnaire."""
    try:
        # Validate resource type
        if questionnaire.get("resourceType") != "Questionnaire":
            raise HTTPException(
                status_code=400,
                detail="Resource must be of type 'Questionnaire'"
            )

        # Ensure ID matches
        if "id" in questionnaire and questionnaire["id"] != questionnaire_id:
            raise HTTPException(
                status_code=400,
                detail="Resource ID does not match URL"
            )

        questionnaire["id"] = questionnaire_id

        resource = await fhir_client.update_resource(
            "Questionnaire",
            questionnaire_id,
            questionnaire
        )

        return resource.serialize()

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{questionnaire_id}")
async def delete_questionnaire(
    questionnaire_id: str,
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """Delete a Questionnaire."""
    try:
        await fhir_client.delete_resource("Questionnaire", questionnaire_id)

        return {
            "message": f"Questionnaire/{questionnaire_id} deleted successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{questionnaire_id}/$package")
async def package_questionnaire(
    questionnaire_id: str,
    fhir_client: FHIRClientService = Depends(get_fhir_client)
):
    """
    Generate a Bundle containing the Questionnaire and all its dependencies
    (ValueSets, CodeSystems, Libraries).

    This implements the SDC $package operation.
    """
    try:
        # Get the questionnaire
        questionnaire = await fhir_client.get_resource("Questionnaire", questionnaire_id)

        if not questionnaire:
            raise HTTPException(
                status_code=404,
                detail=f"Questionnaire/{questionnaire_id} not found"
            )

        # Create bundle with questionnaire
        bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": questionnaire.serialize()}
            ]
        }

        # TODO: Extract referenced ValueSets, CodeSystems, and Libraries
        # For now, return just the Questionnaire
        # Next implementation will add dependency resolution

        logger.info(f"Packaged Questionnaire/{questionnaire_id}")

        return bundle

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error packaging questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
