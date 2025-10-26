"""Pytest configuration and shared fixtures."""
import pytest
import asyncio
import httpx
import time
import logging
import os
import uuid
from typing import Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def generate_unique_id() -> str:
    """Generate a short unique ID for test resources."""
    return str(uuid.uuid4())[:8]


def make_unique_url(base_url: str) -> str:
    """Add unique suffix to URL to prevent collisions."""
    unique_id = generate_unique_id()
    return f"{base_url}-{unique_id}"


# ============================================================================
# FHIR Server Configuration
# ============================================================================

# Server profiles with known behavior differences
SERVER_PROFILES = {
    "hapi": {
        "name": "HAPI FHIR",
        "base_url": "http://localhost:8081/fhir",
        "validation_strict": False,  # HAPI is lenient with validation
        "supports_xml": True,
        "supports_graphql": False,
        "metadata_path": "/metadata",
        "startup_timeout": 120,  # seconds
    },
    "aidbox": {
        "name": "Aidbox",
        "base_url": "http://localhost:8888/fhir",  # Aidbox FHIR endpoint
        "validation_strict": True,  # Aidbox validates strictly
        "supports_xml": True,
        "supports_graphql": True,
        "metadata_path": "/metadata",
        "startup_timeout": 60,
    },
    "azure": {
        "name": "Azure Health Data Services",
        "base_url": os.getenv("AZURE_FHIR_URL", "https://your-fhir.azurehealthcareapis.com"),
        "validation_strict": True,
        "supports_xml": True,
        "supports_graphql": False,
        "metadata_path": "/metadata",
        "requires_auth": True,
        "startup_timeout": 30,
    },
    "firely": {
        "name": "Firely Server",
        "base_url": "http://localhost:4080",
        "validation_strict": True,
        "supports_xml": True,
        "supports_graphql": False,
        "metadata_path": "/metadata",
        "startup_timeout": 60,
    },
    "smile": {
        "name": "Smile CDR",
        "base_url": "https://try.smilecdr.com:8000/baseR4",
        "validation_strict": True,
        "supports_xml": True,
        "supports_graphql": False,
        "metadata_path": "/metadata",
        "startup_timeout": 30,
        "is_public_server": True,  # Don't create/delete resources on public server
        "read_only_mode": True,  # Only run read/search tests
    },
}

# Default server
DEFAULT_FHIR_SERVER = "hapi"

# FastAPI proxy URL (stays the same regardless of FHIR server)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001")


def pytest_addoption(parser):
    """Add custom pytest command line options."""
    parser.addoption(
        "--fhir-server",
        action="store",
        default=DEFAULT_FHIR_SERVER,
        help=f"FHIR server to test against. Options: {', '.join(SERVER_PROFILES.keys())}. "
             f"Default: {DEFAULT_FHIR_SERVER}"
    )
    parser.addoption(
        "--fhir-url",
        action="store",
        default=None,
        help="Override FHIR server base URL (e.g., http://custom-server:8080/fhir)"
    )


@pytest.fixture(scope="session")
def fhir_server_config(request):
    """Get FHIR server configuration based on CLI options."""
    server_name = request.config.getoption("--fhir-server")
    custom_url = request.config.getoption("--fhir-url")

    if server_name not in SERVER_PROFILES:
        pytest.exit(
            f"Unknown FHIR server: {server_name}. "
            f"Available: {', '.join(SERVER_PROFILES.keys())}"
        )

    config = SERVER_PROFILES[server_name].copy()

    # Override URL if provided
    if custom_url:
        config["base_url"] = custom_url
        logger.info(f"Using custom FHIR URL: {custom_url}")

    logger.info(f"Testing against: {config['name']} at {config['base_url']}")
    return config


# ============================================================================
# FHIR Server Client Fixtures
# ============================================================================

@pytest.fixture
async def fhir_server(fhir_server_config):
    """
    FHIR server client for testing.

    Works with any FHIR server (HAPI, Aidbox, Azure, Firely, etc.)
    Waits for server to be ready before yielding client.
    """
    base_url = fhir_server_config["base_url"]
    server_name = fhir_server_config["name"]
    timeout_seconds = fhir_server_config["startup_timeout"]
    metadata_path = fhir_server_config["metadata_path"]

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # Wait for FHIR server to be ready
        logger.info(f"Waiting for {server_name} to be ready at {base_url}...")
        attempts = timeout_seconds // 2

        for attempt in range(attempts):
            try:
                response = await client.get(metadata_path)
                if response.status_code == 200:
                    capability = response.json()
                    fhir_version = capability.get("fhirVersion", "unknown")

                    # Get server version (different servers provide this differently)
                    software = capability.get("software")
                    if software and isinstance(software, dict):
                        server_version = software.get("version", "unknown")
                    else:
                        # Aidbox and others may not include software.version
                        server_version = "unknown (not in CapabilityStatement)"

                    logger.info(
                        f"{server_name} is ready! "
                        f"Server version: {server_version}, "
                        f"FHIR version: {fhir_version}"
                    )
                    break
            except Exception as e:
                logger.debug(
                    f"{server_name} not ready "
                    f"(attempt {attempt + 1}/{attempts}): {e}"
                )
                await asyncio.sleep(2)
        else:
            raise RuntimeError(
                f"{server_name} not ready after {timeout_seconds} seconds. "
                f"Is the server running at {base_url}?"
            )

        yield client


# Backward compatibility alias
@pytest.fixture
async def hapi_client(fhir_server):
    """
    Backward compatibility alias for fhir_server.

    DEPRECATED: Use fhir_server instead.
    This fixture will be removed in a future version.
    """
    return fhir_server


@pytest.fixture
async def cleanup_all_resources(fhir_server, request):
    """
    Optional fixture to clean up ALL test resources.

    Use this explicitly in tests that need a clean slate:
        async def test_something(cleanup_all_resources, fhir_server):
            # Test runs with clean database

    Or call it manually:
        await cleanup_all_resources()
    """
    async def _cleanup():
        # Skip cleanup for read-only servers
        server_profile = request.config.getoption("--fhir-server")
        if server_profile == "smile":
            return

        # Clean up test resources
        resource_types = ['Questionnaire', 'ValueSet', 'CodeSystem', 'Library']

        for resource_type in resource_types:
            try:
                response = await fhir_server.get(f"/{resource_type}")

                if response.status_code == 200:
                    bundle = response.json()
                    entries = bundle.get('entry', [])

                    for entry in entries:
                        try:
                            resource_id = entry['resource']['id']
                            await fhir_server.delete(f"/{resource_type}/{resource_id}")
                            logger.debug(f"Cleaned up {resource_type}/{resource_id}")
                        except Exception as e:
                            logger.debug(f"Could not delete {resource_type}: {e}")

            except Exception as e:
                logger.debug(f"Cleanup error for {resource_type}: {e}")

    # Don't run automatically - just provide the function
    return _cleanup


@pytest.fixture
async def api_client():
    """FastAPI test client."""
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as client:
        # Wait for API to be ready
        logger.info("Waiting for FastAPI test server to be ready...")
        for attempt in range(30):
            try:
                response = await client.get("/health")
                if response.status_code == 200:
                    logger.info("FastAPI test server is ready!")
                    break
            except Exception as e:
                logger.debug(f"API not ready (attempt {attempt + 1}/30): {e}")
                await asyncio.sleep(1)
        else:
            raise RuntimeError("FastAPI not ready after 30 seconds")

        yield client


@pytest.fixture(scope="session")
def server_profile(fhir_server_config):
    """
    Get server profile for conditional test logic.

    Use this to handle server-specific behavior differences.

    Example:
        if server_profile["validation_strict"]:
            assert response.status_code == 400
        else:
            assert response.status_code in [200, 400]
    """
    return fhir_server_config


# ============================================================================
# Resource Creation/Cleanup Fixtures
# ============================================================================

@pytest.fixture
async def clean_questionnaire(fhir_server):
    """
    Create a Questionnaire and clean it up after test.

    Returns a function that creates and tracks Questionnaires.
    """
    created_ids = []

    async def _create(questionnaire: Dict[str, Any]) -> str:
        """Create Questionnaire and track for cleanup."""
        response = await fhir_server.post("/Questionnaire", json=questionnaire)
        response.raise_for_status()
        resource_id = response.json()["id"]
        created_ids.append(resource_id)
        return resource_id

    yield _create

    # Cleanup
    for resource_id in created_ids:
        try:
            await fhir_server.delete(f"/Questionnaire/{resource_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup Questionnaire/{resource_id}: {e}")


@pytest.fixture
async def clean_valueset(fhir_server):
    """
    Create a ValueSet and clean it up after test.
    """
    created_ids = []

    async def _create(valueset: Dict[str, Any]) -> str:
        """Create ValueSet and track for cleanup."""
        response = await fhir_server.post("/ValueSet", json=valueset)
        response.raise_for_status()
        resource_id = response.json()["id"]
        created_ids.append(resource_id)
        return resource_id

    yield _create

    # Cleanup
    for resource_id in created_ids:
        try:
            await fhir_server.delete(f"/ValueSet/{resource_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup ValueSet/{resource_id}: {e}")


@pytest.fixture
async def clean_codesystem(fhir_server):
    """
    Create a CodeSystem and clean it up after test.
    """
    created_ids = []

    async def _create(codesystem: Dict[str, Any]) -> str:
        """Create CodeSystem and track for cleanup."""
        response = await fhir_server.post("/CodeSystem", json=codesystem)
        response.raise_for_status()
        resource_id = response.json()["id"]
        created_ids.append(resource_id)
        return resource_id

    yield _create

    # Cleanup
    for resource_id in created_ids:
        try:
            await fhir_server.delete(f"/CodeSystem/{resource_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup CodeSystem/{resource_id}: {e}")


@pytest.fixture
async def load_test_fixtures(fhir_server):
    """
    Load common test fixtures into FHIR server for testing.

    Returns dict mapping fixture names to resource IDs.
    """
    from tests.fixtures.sample_resources import (
        PHQ2_QUESTIONNAIRE,
        PHQ2_VALUESET,
        PHQ2_CODESYSTEM,
        DIABETES_QUESTIONNAIRE,
        GLUCOSE_VALUESET
    )

    fixtures = {}

    # Load PHQ-2 resources
    try:
        response = await fhir_server.post("/Questionnaire", json=PHQ2_QUESTIONNAIRE)
        fixtures["phq2_questionnaire_id"] = response.json()["id"]

        response = await fhir_server.post("/ValueSet", json=PHQ2_VALUESET)
        fixtures["phq2_valueset_id"] = response.json()["id"]

        response = await fhir_server.post("/CodeSystem", json=PHQ2_CODESYSTEM)
        fixtures["phq2_codesystem_id"] = response.json()["id"]

        logger.info("Loaded PHQ-2 test fixtures")
    except Exception as e:
        logger.warning(f"Failed to load PHQ-2 fixtures: {e}")

    # Load Diabetes resources
    try:
        response = await fhir_server.post("/Questionnaire", json=DIABETES_QUESTIONNAIRE)
        fixtures["diabetes_questionnaire_id"] = response.json()["id"]

        response = await fhir_server.post("/ValueSet", json=GLUCOSE_VALUESET)
        fixtures["glucose_valueset_id"] = response.json()["id"]

        logger.info("Loaded Diabetes test fixtures")
    except Exception as e:
        logger.warning(f"Failed to load Diabetes fixtures: {e}")

    yield fixtures

    # Cleanup all created resources
    for fixture_name, resource_id in fixtures.items():
        try:
            # Extract resource type from fixture name
            if "questionnaire" in fixture_name:
                resource_type = "Questionnaire"
            elif "valueset" in fixture_name:
                resource_type = "ValueSet"
            elif "codesystem" in fixture_name:
                resource_type = "CodeSystem"
            else:
                continue

            await fhir_server.delete(f"/{resource_type}/{resource_id}")
            logger.debug(f"Cleaned up {resource_type}/{resource_id}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {fixture_name} ({resource_id}): {e}")


# Marker for skipping tests if HAPI is not available
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "requires_hapi: mark test as requiring HAPI FHIR server"
    )
