"""The shipped sidecar image (docker-compose.test.yml `fastapi-test`).

All other sidecar tests run the app in-process. This one proves the
container actually starts, serves, and talks to HAPI — i.e. that
api/Dockerfile and the compose wiring are not broken.
"""
import httpx
import pytest

from tests.conftest import SIDECAR_CONTAINER_URL

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_containerized_sidecar_is_healthy_and_packages():
    async with httpx.AsyncClient(base_url=SIDECAR_CONTAINER_URL, timeout=30.0) as client:
        health = await client.get("/health")
        assert health.status_code == 200, (
            f"Sidecar container not reachable at {SIDECAR_CONTAINER_URL} — "
            f"is the test stack up (make test-stack)?"
        )
        body = health.json()
        assert body["status"] == "healthy"
        assert body["version"] not in ("", "dev"), (
            "FORM_MANAGER_VERSION did not reach the container (build-arg → env)"
        )

        # One real round trip through the container to HAPI.
        search = await client.get("/api/questionnaires/search", params={"_count": 1})
        assert search.status_code == 200
        assert search.json()["resourceType"] == "Bundle"
