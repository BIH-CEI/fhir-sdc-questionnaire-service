"""
Enhanced Terminology Proxy for Workshop

Wraps ONTOSERVER with additional LOINC-specific APIs:
- LOINC Panel structure → FHIR Questionnaire
- Answer Lists with ordinal values
- Multi-language ValueSet expansion
- PROMIS scoring service (future)
"""

import os
import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from typing import Optional, List
from cachetools import TTLCache
import logging

# Configuration
ONTOSERVER_URL = os.getenv("ONTOSERVER_URL", "http://ontoserver:8080/fhir")
LOINC_FHIR_URL = os.getenv("LOINC_FHIR_URL", "https://fhir.loinc.org")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
ENABLE_LOINC_PANELS = os.getenv("ENABLE_LOINC_PANELS", "true").lower() == "true"
ENABLE_ORDINAL_VALUES = os.getenv("ENABLE_ORDINAL_VALUES", "true").lower() == "true"

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache for terminology lookups
cache = TTLCache(maxsize=1000, ttl=CACHE_TTL)

app = FastAPI(
    title="Enhanced Terminology Service",
    description="LOINC-enhanced terminology proxy for PROMIS workshop",
    version="1.0.0"
)

# HTTP client
client = httpx.AsyncClient(timeout=30.0)


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()


@app.get("/")
async def root():
    """Service status and capabilities"""
    return {
        "service": "Enhanced Terminology Proxy",
        "version": "1.0.0",
        "capabilities": {
            "loinc_panels": ENABLE_LOINC_PANELS,
            "ordinal_values": ENABLE_ORDINAL_VALUES,
            "multi_language": True,
            "promis_scoring": False  # Not yet implemented
        },
        "endpoints": {
            "fhir": "/fhir/*",
            "loinc_panel": "/loinc/Panel/{code}",
            "loinc_answerlist": "/loinc/AnswerList/{code}",
            "promis_score": "/promis/$calculate-score (coming soon)"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        # Check ONTOSERVER connectivity
        response = await client.get(f"{ONTOSERVER_URL}/metadata", timeout=5.0)
        ontoserver_ok = response.status_code == 200
    except:
        ontoserver_ok = False

    return {
        "status": "healthy" if ontoserver_ok else "degraded",
        "ontoserver": "connected" if ontoserver_ok else "unreachable"
    }


# ============================================================================
# FHIR Proxy - Pass-through to ONTOSERVER
# ============================================================================

@app.api_route("/fhir/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def fhir_proxy(request: Request, path: str):
    """
    Proxy all FHIR requests to ONTOSERVER
    Allows standard FHIR terminology operations
    """
    url = f"{ONTOSERVER_URL}/{path}"

    # Forward query parameters
    if request.url.query:
        url += f"?{request.url.query}"

    # Forward headers (except host)
    headers = dict(request.headers)
    headers.pop("host", None)

    # Forward body for POST/PUT
    body = None
    if request.method in ["POST", "PUT"]:
        body = await request.body()

    try:
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body
        )

        return JSONResponse(
            content=response.json() if response.content else {},
            status_code=response.status_code,
            headers=dict(response.headers)
        )
    except Exception as e:
        logger.error(f"Error proxying to ONTOSERVER: {e}")
        raise HTTPException(status_code=502, detail="Error contacting terminology server")


# ============================================================================
# Enhanced API 1: LOINC Panel Structure
# ============================================================================

@app.get("/loinc/Panel/{loinc_code}")
async def get_loinc_panel(
    loinc_code: str,
    format: str = Query("json", description="Output format: json or Questionnaire")
):
    """
    Get LOINC panel structure

    This API doesn't exist in standard LOINC FHIR service!
    For workshop, we'll return mock data for PROMIS Pain Interference

    Real implementation would:
    1. Query LOINC database for panel members
    2. Get answer lists for each item
    3. Convert to FHIR Questionnaire format
    """

    if not ENABLE_LOINC_PANELS:
        raise HTTPException(status_code=501, detail="LOINC Panel API not enabled")

    # Mock data for questionnaires
    # In production, this would query actual LOINC database

    if loinc_code == "44249-1":  # PHQ-9 Depression Screening
        if format == "Questionnaire":
            return {
                "resourceType": "Questionnaire",
                "id": "phq-9",
                "url": "http://loinc.org/Questionnaire/44249-1",
                "version": "1.0",
                "name": "PHQ9",
                "title": "Patient Health Questionnaire-9 (PHQ-9)",
                "status": "active",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "44249-1",
                    "display": "PHQ-9 quick depression assessment panel"
                }],
                "item": [
                    {
                        "linkId": "44250-9",
                        "code": [{"system": "http://loinc.org", "code": "44250-9"}],
                        "text": "Little interest or pleasure in doing things",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44255-8",
                        "code": [{"system": "http://loinc.org", "code": "44255-8"}],
                        "text": "Feeling down, depressed, or hopeless",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44259-0",
                        "code": [{"system": "http://loinc.org", "code": "44259-0"}],
                        "text": "Trouble falling or staying asleep, or sleeping too much",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44254-1",
                        "code": [{"system": "http://loinc.org", "code": "44254-1"}],
                        "text": "Feeling tired or having little energy",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44251-7",
                        "code": [{"system": "http://loinc.org", "code": "44251-7"}],
                        "text": "Poor appetite or overeating",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44258-2",
                        "code": [{"system": "http://loinc.org", "code": "44258-2"}],
                        "text": "Feeling bad about yourself - or that you are a failure or have let yourself or your family down",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44252-5",
                        "code": [{"system": "http://loinc.org", "code": "44252-5"}],
                        "text": "Trouble concentrating on things, such as reading the newspaper or watching television",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44253-3",
                        "code": [{"system": "http://loinc.org", "code": "44253-3"}],
                        "text": "Moving or speaking so slowly that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    },
                    {
                        "linkId": "44260-8",
                        "code": [{"system": "http://loinc.org", "code": "44260-8"}],
                        "text": "Thoughts that you would be better off dead, or of hurting yourself in some way",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-9"
                    }
                ]
            }
        else:
            return {
                "panel_code": "44249-1",
                "panel_name": "PHQ-9 quick depression assessment panel",
                "items": ["44250-9", "44255-8", "44259-0", "44254-1", "44251-7", "44258-2", "44252-5", "44253-3", "44260-8"]
            }

    elif loinc_code == "62629-8":  # PROMIS Pain Interference 6a
        if format == "Questionnaire":
            return {
                "resourceType": "Questionnaire",
                "id": "promis-pain-interference-6a",
                "url": "http://loinc.org/Questionnaire/62629-8",
                "version": "1.0",
                "name": "PROMISPainInterference6a",
                "title": "PROMIS Pain Interference 6a",
                "status": "active",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "62629-8",
                    "display": "PROMIS pain interference - version 1.0"
                }],
                "item": [
                    {
                        "linkId": "61758-9",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61758-9",
                            "display": "How much did pain interfere with your day to day activities?"
                        }],
                        "text": "How much did pain interfere with your day to day activities?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    },
                    {
                        "linkId": "61769-6",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61769-6",
                            "display": "How much did pain interfere with work around the home?"
                        }],
                        "text": "How much did pain interfere with work around the home?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    },
                    {
                        "linkId": "61773-8",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61773-8",
                            "display": "How much did pain interfere with your ability to participate in social activities?"
                        }],
                        "text": "How much did pain interfere with your ability to participate in social activities?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    },
                    {
                        "linkId": "61777-9",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61777-9",
                            "display": "How much did pain interfere with your household chores?"
                        }],
                        "text": "How much did pain interfere with your household chores?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    },
                    {
                        "linkId": "61781-1",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61781-1",
                            "display": "How much did pain interfere with things you usually do for fun?"
                        }],
                        "text": "How much did pain interfere with things you usually do for fun?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    },
                    {
                        "linkId": "61785-2",
                        "code": [{
                            "system": "http://loinc.org",
                            "code": "61785-2",
                            "display": "How much did pain interfere with your enjoyment of life?"
                        }],
                        "text": "How much did pain interfere with your enjoyment of life?",
                        "type": "choice",
                        "required": True,
                        "answerValueSet": "http://loinc.org/vs/LL358-3"
                    }
                ]
            }
        else:
            return {
                "panel_code": "62629-8",
                "panel_name": "PROMIS pain interference - version 1.0",
                "items": ["61758-9", "61769-6", "61773-8", "61777-9", "61781-1", "61785-2"]
            }

    raise HTTPException(status_code=404, detail=f"LOINC panel {loinc_code} not found")


# ============================================================================
# Enhanced API 2: Answer Lists with Ordinal Values
# ============================================================================

@app.get("/loinc/AnswerList/{answer_list_code}")
async def get_loinc_answerlist(
    answer_list_code: str,
    include_ordinals: bool = Query(True, alias="include", description="Include ordinal values"),
    version: Optional[str] = Query(None, description="Specific version (for version mismatch demo)"),
    display_language: Optional[str] = Query("en", alias="displayLanguage", description="Language code")
):
    """
    Get LOINC answer list with ordinal values

    This is partially missing from standard terminology servers!
    Ordinal values are often not included in ValueSet/$expand

    For workshop demo, we'll show version mismatch:
    - version=1.0: ordinals 1-5 (lower = better)
    - version=2.0: ordinals 5-1 (reversed! higher = better)
    """

    if not ENABLE_ORDINAL_VALUES:
        raise HTTPException(status_code=501, detail="Ordinal values API not enabled")

    # Mock data for PROMIS Pain Interference answer list (LOINC: LL358-3)
    if answer_list_code == "LL358-3":

        # Simulate version mismatch for workshop demo!
        # v1.0: Original PROMIS scoring (1=Not at all, 5=Very much)
        # v2.0: Hypothetical reversal (5=Not at all, 1=Very much)
        # This demonstrates the danger of version mismatches

        ordinals_v1 = {"LA13863-8": 1, "LA13909-9": 2, "LA13902-4": 3, "LA13914-9": 4, "LA13942-0": 5}
        ordinals_v2 = {"LA13863-8": 5, "LA13909-9": 4, "LA13902-4": 3, "LA13914-9": 2, "LA13942-0": 1}

        ordinals = ordinals_v2 if version == "2.0" else ordinals_v1

        # Multi-language support
        translations = {
            "en": {
                "LA13863-8": "Not at all",
                "LA13909-9": "A little bit",
                "LA13902-4": "Somewhat",
                "LA13914-9": "Quite a bit",
                "LA13942-0": "Very much"
            },
            "de": {
                "LA13863-8": "Überhaupt nicht",
                "LA13909-9": "Ein wenig",
                "LA13902-4": "Etwas",
                "LA13914-9": "Ziemlich",
                "LA13942-0": "Sehr stark"
            },
            "tr": {
                "LA13863-8": "Hiç",
                "LA13909-9": "Biraz",
                "LA13902-4": "Bir miktar",
                "LA13914-9": None,  # Missing translation!
                "LA13942-0": None   # Missing translation!
            }
        }

        lang = display_language or "en"

        expansion_contains = []
        for code in ["LA13863-8", "LA13909-9", "LA13902-4", "LA13914-9", "LA13942-0"]:
            item = {
                "code": code,
                "system": "http://loinc.org",
                "display": translations["en"][code]
            }

            # Add designations for requested language
            if lang != "en":
                designations = [{"language": "en", "value": translations["en"][code]}]
                if lang in translations and translations[lang].get(code):
                    designations.append({"language": lang, "value": translations[lang][code]})
                else:
                    # Mark missing translation
                    item["_extension"] = [{
                        "url": "http://workshop.fhir.org/StructureDefinition/translation-status",
                        "valueCode": "missing"
                    }]
                item["designation"] = designations

            # Add ordinal value
            if include_ordinals:
                item["extension"] = [{
                    "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                    "valueDecimal": ordinals[code]
                }]

            expansion_contains.append(item)

        return {
            "resourceType": "ValueSet",
            "id": "ll358-3",
            "url": "http://loinc.org/vs/LL358-3",
            "version": version or "1.0",
            "name": "PROMIS Pain Interference Response",
            "status": "active",
            "expansion": {
                "identifier": f"urn:uuid:workshop-{answer_list_code}",
                "timestamp": "2024-11-27T00:00:00Z",
                "total": len(expansion_contains),
                "parameter": [
                    {"name": "version", "valueString": version or "1.0"},
                    {"name": "displayLanguage", "valueString": lang}
                ],
                "contains": expansion_contains
            }
        }

    # PHQ-9 Answer List (LOINC: LL358-9)
    elif answer_list_code == "LL358-9":

        # PHQ-9 uses simple ordinals (0-3), no version differences
        ordinals = {
            "LA6568-5": 0,  # Not at all
            "LA6569-3": 1,  # Several days
            "LA6570-1": 2,  # More than half the days
            "LA6571-9": 3   # Nearly every day
        }

        # Multi-language support
        translations = {
            "en": {
                "LA6568-5": "Not at all",
                "LA6569-3": "Several days",
                "LA6570-1": "More than half the days",
                "LA6571-9": "Nearly every day"
            },
            "de": {
                "LA6568-5": "Überhaupt nicht",
                "LA6569-3": "An einzelnen Tagen",
                "LA6570-1": "An mehr als der Hälfte der Tage",
                "LA6571-9": "Beinahe jeden Tag"
            },
            "tr": {
                "LA6568-5": "Hiç",
                "LA6569-3": "Birkaç gün",
                "LA6570-1": None,  # Missing translation!
                "LA6571-9": None   # Missing translation!
            }
        }

        lang = display_language or "en"

        expansion_contains = []
        for code in ["LA6568-5", "LA6569-3", "LA6570-1", "LA6571-9"]:
            item = {
                "code": code,
                "system": "http://loinc.org",
                "display": translations["en"][code]
            }

            # Add designations for requested language
            if lang != "en":
                designations = [{"language": "en", "value": translations["en"][code]}]
                if lang in translations and translations[lang].get(code):
                    designations.append({"language": lang, "value": translations[lang][code]})
                else:
                    # Mark missing translation
                    item["_extension"] = [{
                        "url": "http://workshop.fhir.org/StructureDefinition/translation-status",
                        "valueCode": "missing"
                    }]
                item["designation"] = designations

            # Add ordinal value
            if include_ordinals:
                item["extension"] = [{
                    "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                    "valueDecimal": ordinals[code]
                }]

            expansion_contains.append(item)

        return {
            "resourceType": "ValueSet",
            "id": "ll358-9",
            "url": "http://loinc.org/vs/LL358-9",
            "version": version or "1.0",
            "name": "PHQ9 Response",
            "status": "active",
            "expansion": {
                "identifier": f"urn:uuid:workshop-{answer_list_code}",
                "timestamp": "2024-11-27T00:00:00Z",
                "total": len(expansion_contains),
                "parameter": [
                    {"name": "version", "valueString": version or "1.0"},
                    {"name": "displayLanguage", "valueString": lang}
                ],
                "contains": expansion_contains
            }
        }

    raise HTTPException(status_code=404, detail=f"Answer list {answer_list_code} not found")


# ============================================================================
# Enhanced API 3: PROMIS Scoring Service (Placeholder)
# ============================================================================

@app.post("/promis/$calculate-score")
async def calculate_promis_score(request: Request):
    """
    Calculate PROMIS T-score using IRT algorithms

    NOT YET IMPLEMENTED - Placeholder for Phase 2

    Requires:
    - PROMIS IRT parameter tables
    - Psychometric libraries (R/Python)
    - PROMIS licensing agreement
    """

    return {
        "resourceType": "OperationOutcome",
        "issue": [{
            "severity": "information",
            "code": "not-supported",
            "diagnostics": "PROMIS scoring service not yet implemented. This will be available in Phase 2 of the project. For now, use local CQL scoring in HAPI FHIR servers."
        }]
    }


# ============================================================================
# Utility Endpoints
# ============================================================================

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    return {
        "size": len(cache),
        "maxsize": cache.maxsize,
        "ttl": cache.ttl,
        "currsize": cache.currsize
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear the cache"""
    cache.clear()
    return {"status": "cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
