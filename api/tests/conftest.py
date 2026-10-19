"""Pytest configuration and shared fixtures.

Two targets:

- ``fhir_server``: the HAPI Form Manager image (Docker), reached over HTTP.
  ``FHIR_BASE_URL`` (default ``http://localhost:8081/fhir``) or ``--fhir-url``.
- ``api_client``: the FastAPI sidecar. By default the app is imported and
  driven **in-process** through httpx's ASGI transport, talking to the same
  HAPI. That is what makes ``--cov=app`` measure anything. Set
  ``API_BASE_URL`` to target a running sidecar over HTTP instead (black-box
  mode, no coverage).

Unit tests (``tests/unit``) need neither target.
"""
import asyncio
import time
import logging
import os
import uuid
from typing import Any, Dict

import httpx
import pytest

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def generate_unique_id() -> str:
    """Generate a short unique ID for test resources."""
    return str(uuid.uuid4())[:8]


def make_unique_url(base_url: str) -> str:
    """Add unique suffix to URL to prevent collisions."""
    return f"{base_url}-{generate_unique_id()}"


# ============================================================================
# Targets
# ============================================================================

DEFAULT_FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://localhost:8081/fhir")
HAPI_STARTUP_TIMEOUT = 120  # seconds

# Set → black-box mode against a running sidecar. Unset → in-process ASGI.
API_BASE_URL = os.getenv("API_BASE_URL")
# The containerized sidecar's host port in docker-compose.test.yml. Only
# used by the container smoke test.
SIDECAR_CONTAINER_URL = os.getenv("SIDECAR_CONTAINER_URL", "http://localhost:8001")


def pytest_addoption(parser):
    parser.addoption(
        "--fhir-url",
        action="store",
        default=None,
        help="Override FHIR server base URL (default: $FHIR_BASE_URL or "
             f"{DEFAULT_FHIR_BASE_URL})",
    )


@pytest.fixture(scope="session")
def fhir_base_url(request) -> str:
    url = request.config.getoption("--fhir-url") or DEFAULT_FHIR_BASE_URL
    logger.info(f"Testing against HAPI at {url}")
    return url


@pytest.fixture(scope="session")
def _hapi_ready(fhir_base_url) -> None:
    """Wait once per session for HAPI's /metadata."""
    deadline = HAPI_STARTUP_TIMEOUT // 2
    with httpx.Client(base_url=fhir_base_url, timeout=30.0) as client:
        for attempt in range(deadline):
            try:
                response = client.get("/metadata")
                if response.status_code == 200:
                    capability = response.json()
                    software = capability.get("software") or {}
                    logger.info(
                        "HAPI ready: version=%s fhirVersion=%s",
                        software.get("version", "unknown"),
                        capability.get("fhirVersion", "unknown"),
                    )
                    return
            except Exception as e:  # noqa: BLE001 — retry loop
                logger.debug(f"HAPI not ready (attempt {attempt + 1}/{deadline}): {e}")

            time.sleep(2)
    raise RuntimeError(
        f"HAPI not ready after {HAPI_STARTUP_TIMEOUT}s. Is the stack running "
        f"at {fhir_base_url}? (make test-stack)"
    )


# HAPI reuses cached search results for 60 s. Tests create and delete
# resources under the same canonical across runs, so every search must bypass
# the cache (HAPI honours Cache-Control: no-cache).
NO_CACHE = {"Cache-Control": "no-cache"}


@pytest.fixture
async def fhir_server(fhir_base_url, _hapi_ready):
    """HTTP client against HAPI (the Form Manager image)."""
    async with httpx.AsyncClient(base_url=fhir_base_url, timeout=30.0, headers=NO_CACHE) as client:
        yield client


# ----------------------------------------------------------------------------
# Sidecar: in-process by default
# ----------------------------------------------------------------------------

def _load_app(fhir_base_url: str):
    """Import the FastAPI app with FHIR_BASE_URL pointing at the test HAPI.

    Settings are read at import time (lru_cache), so the env var must be in
    place before the first import of ``app``.
    """
    os.environ["FHIR_BASE_URL"] = fhir_base_url
    os.environ.setdefault("LOG_LEVEL", "warning")
    from app.main import app  # noqa: WPS433 — deliberate late import
    return app


@pytest.fixture(scope="session")
def sidecar_app(fhir_base_url):
    if API_BASE_URL:
        return None
    return _load_app(fhir_base_url)


@pytest.fixture(autouse=True)
async def _reset_sidecar_singletons(sidecar_app):
    """Give every test fresh service singletons.

    The sidecar keeps module-level singletons holding httpx/aiohttp clients.
    pytest-asyncio runs each test on its own event loop; a connection pool
    created on a previous loop must not be reused. Reset before, close after.
    """
    if sidecar_app is None:
        yield
        return

    from app.routers import questionnaires as q_router
    from app.services import fhir_client as fc

    q_router._package_service = None
    q_router._localization_service = None
    q_router._scoring_extract_service = None
    fc._fhir_client = None
    yield
    if q_router._package_service is not None:
        await q_router._package_service.close()
    if q_router._scoring_extract_service is not None:
        await q_router._scoring_extract_service.aclose()
    q_router._package_service = None
    q_router._localization_service = None
    q_router._scoring_extract_service = None
    fc._fhir_client = None
    sidecar_app.dependency_overrides.clear()


@pytest.fixture
async def api_client(sidecar_app, _hapi_ready):
    """Client for the FastAPI sidecar (in-process ASGI, or HTTP if API_BASE_URL)."""
    if sidecar_app is not None:
        transport = httpx.ASGITransport(app=sidecar_app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://sidecar.test", timeout=60.0
        ) as client:
            yield client
        return

    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as client:
        for attempt in range(30):
            try:
                if (await client.get("/health")).status_code == 200:
                    break
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Sidecar not ready (attempt {attempt + 1}/30): {e}")
            await asyncio.sleep(1)
        else:
            raise RuntimeError(f"Sidecar not ready after 30s at {API_BASE_URL}")
        yield client


# ============================================================================
# Resource Creation/Cleanup Fixtures
# ============================================================================

def _tracked_creator(fhir_server, resource_type: str):
    created_ids = []

    async def _create(resource: Dict[str, Any]) -> str:
        response = await fhir_server.post(f"/{resource_type}", json=resource)
        response.raise_for_status()
        resource_id = response.json()["id"]
        created_ids.append(resource_id)
        return resource_id

    async def _cleanup():
        for resource_id in created_ids:
            try:
                await fhir_server.delete(f"/{resource_type}/{resource_id}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to cleanup {resource_type}/{resource_id}: {e}")

    return _create, _cleanup


@pytest.fixture
async def clean_questionnaire(fhir_server):
    """Create Questionnaires that are deleted on teardown."""
    create, cleanup = _tracked_creator(fhir_server, "Questionnaire")
    yield create
    await cleanup()


@pytest.fixture
async def clean_valueset(fhir_server):
    create, cleanup = _tracked_creator(fhir_server, "ValueSet")
    yield create
    await cleanup()


@pytest.fixture
async def clean_codesystem(fhir_server):
    create, cleanup = _tracked_creator(fhir_server, "CodeSystem")
    yield create
    await cleanup()


@pytest.fixture
async def clean_library(fhir_server):
    create, cleanup = _tracked_creator(fhir_server, "Library")
    yield create
    await cleanup()


@pytest.fixture
async def test_subject(fhir_server):
    """A throwaway Patient. On teardown, delete everything that was written
    for it (Observations, QuestionnaireResponses) and the Patient itself, so
    repeated runs against one stack do not accumulate data."""
    r = await fhir_server.post(
        "/Patient",
        json={"resourceType": "Patient",
              "name": [{"family": f"Test-{uuid.uuid4().hex[:6]}"}]},
    )
    r.raise_for_status()
    patient_ref = f"Patient/{r.json()['id']}"
    yield patient_ref
    for rtype in ("Observation", "QuestionnaireResponse"):
        try:
            await fhir_server.delete(f"/{rtype}", params={"subject": patient_ref})
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Cleanup of {rtype} for {patient_ref} failed: {e}")
    try:
        await fhir_server.delete(f"/{patient_ref}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Cleanup of {patient_ref} failed: {e}")


@pytest.fixture
async def load_test_fixtures(fhir_server, clean_questionnaire, clean_valueset, clean_codesystem):
    """Load the synthetic PHQ-2 / diabetes fixtures; all deleted on teardown."""
    from tests.fixtures.sample_resources import (
        DIABETES_QUESTIONNAIRE,
        GLUCOSE_VALUESET,
        PHQ2_CODESYSTEM,
        PHQ2_QUESTIONNAIRE,
        PHQ2_VALUESET,
    )

    return {
        "phq2_questionnaire_id": await clean_questionnaire(PHQ2_QUESTIONNAIRE),
        "phq2_valueset_id": await clean_valueset(PHQ2_VALUESET),
        "phq2_codesystem_id": await clean_codesystem(PHQ2_CODESYSTEM),
        "diabetes_questionnaire_id": await clean_questionnaire(DIABETES_QUESTIONNAIRE),
        "glucose_valueset_id": await clean_valueset(GLUCOSE_VALUESET),
    }


# ============================================================================
# Real MII PRO content — pre-loaded by the container at boot time
# ============================================================================

# Canonical URLs of MII PRO Questionnaires that the Form Manager image
# guarantees to ship and load (version: see Dockerfile.form-manager
# MII_PRO_VERSION). Tests that hit these can skip the fragile
# upload-then-resolve dance — content is deterministic and always present.
PRO_NAMESPACE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire"
PRO_QUESTIONNAIRE_CANONICALS = {
    # 2 external answerValueSet bindings (qlq-c30-scale-4pt / -7pt),
    # each VS in turn binds CodeSystem mii-cs-pro-eortc-qlq-c30 →
    # full Q → VS → CS chain, ideal for transitive-dep tests.
    # (Since 2027 the plain QLQ-C30 carries this chain; the former
    # variant-a/-b Questionnaires were dropped upstream.)
    "qlq_c30":           f"{PRO_NAMESPACE}/mii-qst-pro-eortc-qlq-c30",
    # No answerValueSet at all — for baseline structural tests
    # (Bundle.type, first-entry, no-deps minimal bundle, SDC tags, etc.).
    "phq_9":             f"{PRO_NAMESPACE}/mii-qst-pro-phq-9",
}

# PRO Library (BIH-CEI provisional, 0.x line) — companion content package.
# These canonicals live under the provisional namespace
# https://fhir.bih-charite.de/pro-library and are produced by
# https://github.com/BIH-CEI/pro-library (FSH/SUSHI).
PRO_LIBRARY_NAMESPACE = "https://fhir.bih-charite.de/pro-library"


def _load_pro_library_version() -> str:
    """Single source of truth: PRO_LIBRARY_VERSION env, else versions.env at
    repo root, else fail loudly. Never hardcode the version in tests."""
    env = os.getenv("PRO_LIBRARY_VERSION")
    if env:
        return env
    versions_env = os.path.join(os.path.dirname(__file__), "..", "..", "versions.env")
    if os.path.isfile(versions_env):
        with open(versions_env) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("PRO_LIBRARY_VERSION="):
                    return line.split("=", 1)[1].strip()
    raise RuntimeError("PRO_LIBRARY_VERSION not set and versions.env not found / lacks entry")


PRO_LIBRARY_VERSION = _load_pro_library_version()


def _dockerfile_arg(name: str) -> str:
    """Upstream pins (MII PRO version, retained versions) live only in
    Dockerfile.form-manager ARGs. Env wins (CI exports them); else parse."""
    env = os.getenv(name)
    if env is not None:
        return env
    dockerfile = os.path.join(os.path.dirname(__file__), "..", "..", "Dockerfile.form-manager")
    with open(dockerfile) as fh:
        for line in fh:
            if line.startswith(f"ARG {name}="):
                return line.split("=", 1)[1].strip().strip('"')
    raise RuntimeError(f"ARG {name} not found in Dockerfile.form-manager and not in env")


MII_PRO_VERSION = _dockerfile_arg("MII_PRO_VERSION")
MII_PRO_RETAINED_VERSIONS = _dockerfile_arg("MII_PRO_RETAINED_VERSIONS").split()
MII_PRO_PACKAGE = "de.medizininformatikinitiative.kerndatensatz.pros"
MII_PRO_BASE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro"
PCOR_MII_VERSION = os.getenv("PCOR_MII_VERSION") or next(
    (line.split("=", 1)[1].strip()
     for line in open(os.path.join(os.path.dirname(__file__), "..", "..", "versions.env"))
     if line.startswith("PCOR_MII_VERSION=")),
    None,
)
PRO_LIBRARY_CANONICALS = {
    "phq_9":           f"{PRO_LIBRARY_NAMESPACE}/Questionnaire/phq-9",
    "sf4a":            f"{PRO_LIBRARY_NAMESPACE}/Questionnaire/promis-depression-sf4a",
    # Release-manifest id mirrors the version with dots replaced by dashes,
    # matching the pro-library FSH naming convention.
    "release_manifest": (
        f"{PRO_LIBRARY_NAMESPACE}/Library/"
        f"release-{PRO_LIBRARY_VERSION.replace('.', '-')}"
    ),
}


@pytest.fixture(scope="session")
def pro_questionnaires(fhir_base_url, _hapi_ready) -> Dict[str, Dict[str, Any]]:
    """
    Resolve MII PRO Questionnaires that the container ships pre-loaded.

    Returns dict of short-name → {"id", "url", "version"} for each entry in
    PRO_QUESTIONNAIRE_CANONICALS, at the CURRENT MII_PRO_VERSION (retained
    older versions coexist on the server). Fails the test run loudly if a
    referenced PRO Questionnaire is missing — that means the container's IG
    bundling is broken, not the test. Resolved once per session.
    """
    resolved: Dict[str, Dict[str, Any]] = {}
    with httpx.Client(base_url=fhir_base_url, timeout=30.0, headers=NO_CACHE) as client:
        for short_name, canonical in PRO_QUESTIONNAIRE_CANONICALS.items():
            response = client.get(
                "/Questionnaire",
                params={"url": canonical, "version": MII_PRO_VERSION, "_summary": "true"},
            )
            response.raise_for_status()
            bundle = response.json()
            if bundle.get("total", 0) == 0 or not bundle.get("entry"):
                pytest.fail(
                    f"MII PRO Questionnaire not found in container: {canonical}. "
                    f"The Form Manager image is supposed to bake this in — check "
                    f"Dockerfile.form-manager and the IG install step."
                )
            entry = bundle["entry"][0]["resource"]
            resolved[short_name] = {
                "id": entry["id"],
                "url": entry["url"],
                "version": entry.get("version"),
            }
    return resolved
