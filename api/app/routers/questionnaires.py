"""Questionnaire API endpoints."""
from fastapi import APIRouter, HTTPException, Query, Depends, Body, Path
from typing import Optional, List
from app.services import (
    get_fhir_client,
    FHIRClientService,
    PackageService,
    ScoringExtractService,
)
from app.services.localization_service import LocalizationService
from app.config import get_settings
import httpx
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(
    prefix="/api/questionnaires",
    tags=["questionnaires"],
)

# Service singletons
_package_service = None
_localization_service = None
_scoring_extract_service = None


def get_package_service() -> PackageService:
    """Get singleton package service instance."""
    global _package_service
    if _package_service is None:
        _package_service = PackageService(settings.fhir_base_url)
    return _package_service


def get_scoring_extract_service() -> ScoringExtractService:
    """Get singleton scoring-extract service instance."""
    global _scoring_extract_service
    if _scoring_extract_service is None:
        _scoring_extract_service = ScoringExtractService(settings.fhir_base_url)
    return _scoring_extract_service


def get_localization_service() -> LocalizationService:
    """Get singleton localization service instance."""
    global _localization_service
    if _localization_service is None:
        _localization_service = LocalizationService()
    return _localization_service


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


@router.get("/{questionnaire_id}/$languages", response_model=dict)
async def get_available_languages(
    questionnaire_id: str = Path(..., description="Questionnaire ID"),
    package_service: PackageService = Depends(get_package_service),
    localization_service: LocalizationService = Depends(get_localization_service)
):
    """
    Get list of available languages for a Questionnaire (custom operation).

    This is a convenience operation (not part of SDC specification) to help
    clients discover available languages before calling $localize.

    **Example:**
    ```
    GET /api/questionnaires/diabetes-screening/$languages
    ```

    Returns:
    ```json
    {
      "resourceType": "Parameters",
      "parameter": [
        {"name": "language", "valueCode": "en"},
        {"name": "language", "valueCode": "de"},
        {"name": "language", "valueCode": "es"}
      ]
    }
    ```
    """
    try:
        # Fetch Questionnaire
        questionnaire_response = await package_service.fetch_resource(
            f"/Questionnaire/{questionnaire_id}"
        )

        if not questionnaire_response:
            raise ValueError(f"Questionnaire with id '{questionnaire_id}' not found")

        # Get available languages
        languages = localization_service.get_available_languages(questionnaire_response)

        # Return as FHIR Parameters resource
        return {
            "resourceType": "Parameters",
            "parameter": [
                {"name": "language", "valueCode": lang}
                for lang in languages
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting languages for questionnaire {questionnaire_id}: {e}")
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


@router.post("/$package", response_model=dict)
async def package_questionnaire_resource(
    questionnaire: dict = Body(
        ...,
        description="Questionnaire resource to package"
    ),
    include_dependencies: bool = Query(
        True,
        alias="include-dependencies",
        description="Include transitive dependencies — matches the SDC "
        "`$package` parameter name (hyphenated, per the OperationDefinition).",
    ),
    package_service: PackageService = Depends(get_package_service)
):
    """
    Package a provided Questionnaire resource (SDC $package operation - type level).

    Note: Questionnaire is NOT persisted to the server.
    Dependencies are fetched from the HAPI FHIR server.

    This is useful for packaging a Questionnaire that is still under development
    and not yet saved to the server.

    **Example:**
    ```
    POST /api/questionnaires/$package
    Content-Type: application/json

    {
      "resourceType": "Questionnaire",
      "status": "draft",
      "item": [...]
    }
    ```
    """
    try:
        bundle = await package_service.package_resource(
            questionnaire,
            include_dependencies
        )

        logger.info(
            f"Packaged provided Questionnaire with "
            f"{len(bundle.get('entry', []))} entries"
        )

        return bundle

    except ValueError as e:
        if "must be of type 'Questionnaire'" in str(e):
            raise HTTPException(status_code=422, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error packaging questionnaire resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/$package", response_model=dict)
async def package_questionnaire_by_url(
    url: str = Query(..., description="Canonical URL of Questionnaire"),
    version: Optional[str] = Query(
        None,
        description="Specific version (if not specified, returns latest active version)"
    ),
    include_dependencies: bool = Query(
        True,
        alias="include-dependencies",
        description="Include transitive dependencies — matches the SDC "
        "`$package` parameter name (hyphenated, per the OperationDefinition).",
    ),
    package_service: PackageService = Depends(get_package_service)
):
    """
    Package a Questionnaire by canonical URL (SDC $package operation - type level by URL).

    If version is not specified, returns the latest active version.

    **Example:**
    ```
    GET /api/questionnaires/$package?url=http://example.org/Questionnaire/diabetes
    GET /api/questionnaires/$package?url=http://example.org/Questionnaire/diabetes&version=2.0.0
    ```
    """
    try:
        bundle = await package_service.package_by_url(
            url,
            version,
            include_dependencies
        )

        logger.info(
            f"Packaged Questionnaire by URL '{url}' (version: {version or 'latest'}) "
            f"with {len(bundle.get('entry', []))} entries"
        )

        return bundle

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error packaging questionnaire by URL {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{questionnaire_id}/$package", response_model=dict)
async def package_questionnaire_by_id(
    questionnaire_id: str = Path(..., description="Questionnaire ID"),
    include_dependencies: bool = Query(
        True,
        alias="include-dependencies",
        description="Include transitive dependencies (ValueSets, CodeSystems, "
        "Libraries) — matches the SDC `$package` parameter name.",
    ),
    package_service: PackageService = Depends(get_package_service)
):
    """
    Package a Questionnaire with all its dependencies (SDC $package operation - instance level).

    Returns a FHIR Bundle containing:
    - The Questionnaire
    - All referenced ValueSets
    - All referenced CodeSystems
    - All referenced Libraries
    - All referenced StructureMaps
    - OperationOutcomes for any warnings

    **Example:**
    ```
    GET /api/questionnaires/diabetes-screening/$package
    GET /api/questionnaires/phq-9/$package?include-dependencies=false
    ```
    """
    try:
        bundle = await package_service.package_by_id(
            questionnaire_id,
            include_dependencies
        )

        logger.info(
            f"Packaged Questionnaire/{questionnaire_id} with "
            f"{len(bundle.get('entry', []))} entries"
        )

        return bundle

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error packaging questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# $localize Operation - Extract language-specific version
# ============================================================================

@router.get("/{questionnaire_id}/$localize", response_model=dict)
async def localize_questionnaire_by_id(
    questionnaire_id: str = Path(..., description="Questionnaire ID"),
    language: str = Query(..., description="Target language code (e.g., 'de', 'es', 'fr')"),
    package_service: PackageService = Depends(get_package_service),
    localization_service: LocalizationService = Depends(get_localization_service)
):
    """
    Localize a Questionnaire to a specific language (instance level).

    Extracts a single-language version from a multilingual Questionnaire by:
    - Replacing text with translations for the specified language
    - Removing all translation extensions
    - Setting the language field to the target language

    **Example:**
    ```
    GET /api/questionnaires/diabetes-screening/$localize?language=de
    ```

    Returns a Questionnaire with all text in German, no translation extensions.
    """
    try:
        # Fetch Questionnaire from HAPI
        questionnaire_response = await package_service.fetch_resource(
            f"/Questionnaire/{questionnaire_id}"
        )

        if not questionnaire_response:
            raise ValueError(f"Questionnaire with id '{questionnaire_id}' not found")

        # Localize to target language
        localized = localization_service.localize(
            questionnaire_response,
            language
        )

        logger.info(
            f"Localized Questionnaire/{questionnaire_id} to {language}"
        )

        return localized

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error localizing questionnaire {questionnaire_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/$localize", response_model=dict)
async def localize_questionnaire_resource(
    questionnaire: dict = Body(
        ...,
        description="Questionnaire resource to localize"
    ),
    language: str = Query(..., description="Target language code"),
    localization_service: LocalizationService = Depends(get_localization_service)
):
    """
    Localize a provided Questionnaire resource (type level).

    Note: Questionnaire is NOT persisted to the server.

    **Example:**
    ```
    POST /api/questionnaires/$localize?language=es
    Content-Type: application/json

    {
      "resourceType": "Questionnaire",
      "title": "Patient Health Questionnaire",
      "_title": {
        "extension": [{
          "url": "http://hl7.org/fhir/StructureDefinition/translation",
          "extension": [
            {"url": "lang", "valueCode": "es"},
            {"url": "content", "valueString": "Cuestionario de salud del paciente"}
          ]
        }]
      },
      ...
    }
    ```

    Returns Questionnaire with title="Cuestionario de salud del paciente", no extensions.
    """
    try:
        # Validate resource type
        if questionnaire.get("resourceType") != "Questionnaire":
            raise ValueError("Resource must be of type 'Questionnaire'")

        # Localize to target language
        localized = localization_service.localize(questionnaire, language)

        logger.info(f"Localized provided Questionnaire to {language}")

        return localized

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error localizing questionnaire resource: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/$localize", response_model=dict)
async def localize_questionnaire_by_url(
    url: str = Query(..., description="Canonical URL of Questionnaire"),
    language: str = Query(..., description="Target language code"),
    version: Optional[str] = Query(
        None,
        description="Specific version (if not specified, returns latest active version)"
    ),
    package_service: PackageService = Depends(get_package_service),
    localization_service: LocalizationService = Depends(get_localization_service)
):
    """
    Localize a Questionnaire by canonical URL (type level by URL).

    **Example:**
    ```
    GET /api/questionnaires/$localize?url=http://example.org/Questionnaire/phq9&language=fr
    GET /api/questionnaires/$localize?url=http://example.org/Questionnaire/phq9&version=2.0.0&language=fr
    ```
    """
    try:
        # Search for Questionnaire
        search_params = {"url": url}
        if version:
            search_params["version"] = version
        else:
            search_params["status"] = "active"
            search_params["_sort"] = "-_lastUpdated"
            search_params["_count"] = "1"

        search_result = await package_service.fetch_resource(
            "/Questionnaire",
            params=search_params
        )

        if not search_result or search_result.get("total", 0) == 0:
            raise ValueError(f"Questionnaire with url '{url}' not found")

        questionnaire = search_result["entry"][0]["resource"]

        # Localize to target language
        localized = localization_service.localize(questionnaire, language)

        logger.info(
            f"Localized Questionnaire by URL '{url}' (version: {version or 'latest'}) "
            f"to {language}"
        )

        return localized

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error localizing questionnaire by URL {url}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# $compute-and-extract
# ============================================================================
# Bridges the HAPI CR / SDC gap: HAPI CR's $populate doesn't evaluate
# sdc-calculatedExpression, and HAPI's $extract requires the QR to already
# carry score-item values. This operation orchestrates Library/$evaluate +
# Observation-construction internally, so a consumer makes ONE call:
#
#   POST /api/questionnaires/{id}/$compute-and-extract
#   Body: { "resourceType": "Parameters",
#           "parameter": [{"name":"subject","valueReference":{"reference":"Patient/X"}}] }
#
# Returns a Bundle:
#   - persist=true (default): 'collection' Bundle of the persisted Observations
#   - persist=false:           'transaction' Bundle the caller can POST themselves
#
# Observations are constructed generically from FHIR content (no per-
# instrument code): Questionnaire.item.code → Observation.code (LOINC),
# the item's calculatedExpression names the CQL define that produces the
# value, and ObservationDefinition.qualifiedInterval on the server supplies
# severity-band interpretation. Adding a new instrument is purely a pro-
# library change. See scoring_extract_service.py for details.

@router.post("/{questionnaire_id}/$compute-and-extract", response_model=dict)
async def compute_and_extract(
    questionnaire_id: str = Path(..., description="Questionnaire id (e.g. 'phq-9')"),
    body: dict = Body(
        ...,
        description="Parameters resource with name='subject', valueReference",
        example={
            "resourceType": "Parameters",
            "parameter": [
                {"name": "subject", "valueReference": {"reference": "Patient/example"}}
            ],
        },
    ),
    persist: bool = Query(
        True,
        description="Persist resulting Observations as a transaction (default true). "
                    "If false, returns the transaction Bundle for caller-side persistence.",
    ),
    service: ScoringExtractService = Depends(get_scoring_extract_service),
):
    """
    Compute scoring CQL for a subject + produce Observation resource(s).

    Bridges the SDC-flow gap where HAPI CR doesn't auto-evaluate
    sdc-calculatedExpression. Internally: invokes the bound scoring Library
    via $evaluate, builds Observations from the result with proper LOINC
    codes and (where applicable) Observation.interpretation for severity
    bands, optionally persists them as a transaction.
    """
    # Extract subject from Parameters body
    subject_reference = None
    for p in body.get("parameter", []):
        if p.get("name") == "subject":
            ref = p.get("valueReference", {}).get("reference") or p.get("valueString")
            if ref:
                subject_reference = ref
                break

    if not subject_reference:
        raise HTTPException(
            status_code=400,
            detail="Missing required 'subject' parameter (Patient reference)",
        )

    try:
        bundle = await service.compute_and_extract(
            questionnaire_id=questionnaire_id,
            subject_reference=subject_reference,
            persist=persist,
        )
        logger.info(
            f"$compute-and-extract: questionnaire={questionnaire_id} "
            f"subject={subject_reference} persist={persist} "
            f"entries={len(bundle.get('entry', []))}"
        )
        return bundle

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except httpx.HTTPStatusError as e:
        # Translate upstream FHIR errors so a missing Questionnaire becomes 404
        # instead of 500. Anything else upstream is surfaced as-is.
        upstream = e.response.status_code if e.response is not None else 502
        detail = f"Upstream FHIR server returned {upstream}: {str(e)[:200]}"
        if upstream == 404:
            raise HTTPException(status_code=404, detail=detail)
        raise HTTPException(status_code=502, detail=detail)
    except Exception as e:
        logger.exception(
            f"$compute-and-extract failed for q={questionnaire_id} subject={subject_reference}"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ─── FHIR routing fix: literal `/$<op>` routes must match before wildcards ──
#
# FHIR R4 reserves `$` for operations, and the `id` datatype regex
# ([A-Za-z0-9\-\.]{1,64}) makes `$package` a structurally-invalid id.
# Starlette/FastAPI dispatches in registration order, so without this
# re-sort, `/{questionnaire_id}` would catch `/$package` first and our
# sidecar would forward `$package` to HAPI as if it were a Questionnaire id.
# Stable sort: routes whose first non-prefix segment is a literal (not
# `{wildcard}`) come first. CRMI, SDC and FHIR all rely on this.
def _wildcard_first(route) -> bool:
    parts = route.path[len(router.prefix):].lstrip("/").split("/", 1)
    return bool(parts and parts[0].startswith("{"))


router.routes.sort(key=_wildcard_first)
