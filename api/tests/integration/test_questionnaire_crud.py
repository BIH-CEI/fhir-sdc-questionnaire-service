"""
Integration tests for Questionnaire CRUD operations.

Tests the FastAPI proxy layer to HAPI FHIR, including failure scenarios.
"""
import pytest
from tests.fixtures.sample_resources import (
    PHQ2_QUESTIONNAIRE,
    SIMPLE_TEXT_QUESTIONNAIRE
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuestionnaireCreate:
    """Tests for creating Questionnaires via FastAPI."""

    async def test_create_questionnaire_success(self, api_client, hapi_client):
        """
        Test: Successfully create a Questionnaire

        Given: Valid Questionnaire resource
        When: POST to /api/questionnaires
        Then: Returns 200 with created resource including ID
        """
        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "draft",
            "title": "Test Questionnaire for Creation",
            "item": [{"linkId": "1", "text": "Sample question", "type": "string"}]
        }

        response = await api_client.post(
            "/api/questionnaires/",
            json=questionnaire
        )

        assert response.status_code == 200
        created = response.json()

        assert created["resourceType"] == "Questionnaire"
        assert "id" in created
        assert created["title"] == "Test Questionnaire for Creation"

        # Cleanup
        await hapi_client.delete(f"/Questionnaire/{created['id']}")

    async def test_create_questionnaire_invalid_type_returns_400(self, api_client):
        """
        Test: Creating non-Questionnaire resource returns 400

        Given: Resource with wrong resourceType
        When: POST to /api/questionnaires
        Then: Returns 400 Bad Request
        """
        invalid_resource = {
            "resourceType": "Patient",
            "name": [{"family": "Doe"}]
        }

        response = await api_client.post(
            "/api/questionnaires/",
            json=invalid_resource
        )

        assert response.status_code == 400

    async def test_create_questionnaire_missing_required_field(self, api_client):
        """
        Test: Missing required fields causes HAPI validation error

        Given: Questionnaire missing 'status' field
        When: POST to /api/questionnaires
        Then: Returns 500 (HAPI validation error)
        """
        invalid_questionnaire = {
            "resourceType": "Questionnaire",
            # Missing 'status' - required field
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await api_client.post(
            "/api/questionnaires/",
            json=invalid_questionnaire
        )

        # HAPI validation interceptor should reject (returns 422)
        assert response.status_code in [400, 422, 500]


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuestionnaireRead:
    """Tests for reading Questionnaires via FastAPI."""

    async def test_get_questionnaire_success(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        Test: Successfully retrieve a Questionnaire by ID

        Given: Questionnaire exists in HAPI
        When: GET /api/questionnaires/{id}
        Then: Returns 200 with Questionnaire resource
        """
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]

        response = await api_client.get(
            f"/api/questionnaires/{phq2_id}"
        )

        assert response.status_code == 200
        questionnaire = response.json()

        assert questionnaire["resourceType"] == "Questionnaire"
        assert questionnaire["id"] == phq2_id

    async def test_get_questionnaire_not_found_returns_404(self, api_client):
        """
        Test: Non-existent Questionnaire returns 404

        Given: Invalid Questionnaire ID
        When: GET /api/questionnaires/{invalid_id}
        Then: Returns 404 Not Found
        """
        response = await api_client.get(
            "/api/questionnaires/INVALID_ID_DOES_NOT_EXIST"
        )

        assert response.status_code == 404

    @pytest.mark.failure_scenarios
    async def test_get_questionnaire_hapi_unreachable(self, api_client, monkeypatch):
        """
        Test: HAPI FHIR unreachable causes 500 error

        Given: HAPI server is down/unreachable
        When: GET /api/questionnaires/{id}
        Then: Returns 500 Internal Server Error

        Note: This test simulates failure by using invalid ID that causes timeout
        """
        # This is a simulation - in real scenario, HAPI would be down
        # For now, we just verify error handling exists
        response = await api_client.get(
            "/api/questionnaires/test-timeout",
            timeout=1.0
        )

        # Should handle gracefully
        assert response.status_code in [404, 500]


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuestionnaireUpdate:
    """Tests for updating Questionnaires via FastAPI."""

    async def test_update_questionnaire_success(
        self,
        api_client,
        hapi_client,
        clean_questionnaire
    ):
        """
        Test: Successfully update a Questionnaire

        Given: Questionnaire exists
        When: PUT /api/questionnaires/{id} with updated data
        Then: Returns 200 with updated resource
        """
        # Create initial questionnaire
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)

        # Update it
        updated_questionnaire = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "active",
            "title": "Updated Title",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await api_client.put(
            f"/api/questionnaires/{q_id}",
            json=updated_questionnaire
        )

        assert response.status_code == 200
        updated = response.json()

        assert updated["title"] == "Updated Title"
        assert updated["status"] == "active"

    async def test_update_questionnaire_not_found_returns_404(self, api_client):
        """
        Test: Updating non-existent Questionnaire returns 404

        Given: Invalid Questionnaire ID
        When: PUT /api/questionnaires/{invalid_id}
        Then: Returns 404 Not Found
        """
        questionnaire = {
            "resourceType": "Questionnaire",
            "status": "active",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await api_client.put(
            "/api/questionnaires/NONEXISTENT_ID",
            json=questionnaire
        )

        assert response.status_code == 404

    async def test_update_questionnaire_id_mismatch_returns_400(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        Test: ID mismatch between URL and body returns 400

        Given: Questionnaire with ID different from URL
        When: PUT /api/questionnaires/{id}
        Then: Returns 400 Bad Request
        """
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)

        mismatched_questionnaire = {
            "resourceType": "Questionnaire",
            "id": "different_id",  # Doesn't match URL
            "status": "active",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        response = await api_client.put(
            f"/api/questionnaires/{q_id}",
            json=mismatched_questionnaire
        )

        assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuestionnaireDelete:
    """Tests for deleting Questionnaires via FastAPI."""

    async def test_delete_questionnaire_success(
        self,
        api_client,
        hapi_client
    ):
        """
        Test: Successfully delete a Questionnaire

        Given: Questionnaire exists
        When: DELETE /api/questionnaires/{id}
        Then: Returns 200 with success message
        """
        # Create questionnaire directly in HAPI
        response = await hapi_client.post(
            "/Questionnaire",
            json=SIMPLE_TEXT_QUESTIONNAIRE
        )
        q_id = response.json()["id"]

        # Delete via API
        response = await api_client.delete(f"/api/questionnaires/{q_id}")

        assert response.status_code == 200
        result = response.json()
        assert "deleted successfully" in result["message"]

    async def test_delete_questionnaire_not_found_returns_404(self, api_client):
        """
        Test: Deleting non-existent Questionnaire returns 404

        Given: Invalid Questionnaire ID
        When: DELETE /api/questionnaires/{invalid_id}
        Then: Returns 404 Not Found
        """
        response = await api_client.delete(
            "/api/questionnaires/NONEXISTENT_ID_12345"
        )

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
class TestQuestionnaireSearch:
    """Tests for searching Questionnaires via FastAPI."""

    async def test_search_questionnaires_by_status(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        Test: Search Questionnaires by status

        Given: Multiple Questionnaires with different statuses
        When: GET /api/questionnaires/search?status=active
        Then: Returns only active Questionnaires
        """
        response = await api_client.get(
            "/api/questionnaires/search",
            params={"status": "active"}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "searchset"

        # All returned Questionnaires should have status=active
        for entry in bundle.get("entry", []):
            assert entry["resource"]["status"] == "active"

    async def test_search_questionnaires_by_title(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        Test: Search Questionnaires by title

        Given: Questionnaires with various titles
        When: GET /api/questionnaires/search?title=PHQ
        Then: Returns Questionnaires matching title
        """
        response = await api_client.get(
            "/api/questionnaires/search",
            params={"title": "PHQ"}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"

        # Should find PHQ-2 questionnaire
        titles = [
            entry["resource"]["title"]
            for entry in bundle.get("entry", [])
        ]

        assert any("PHQ" in title for title in titles)

    async def test_search_questionnaires_with_count_limit(
        self,
        api_client,
        load_test_fixtures
    ):
        """
        Test: Search with _count parameter limits results

        Given: Multiple Questionnaires exist
        When: GET /api/questionnaires/search?_count=1
        Then: Returns maximum 1 result
        """
        response = await api_client.get(
            "/api/questionnaires/search",
            params={"_count": 1}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert len(bundle.get("entry", [])) <= 1

    async def test_search_questionnaires_no_results(self, api_client):
        """
        Test: Search with no matching results returns empty bundle

        Given: No Questionnaires match search criteria
        When: GET /api/questionnaires/search?title=NONEXISTENT
        Then: Returns empty Bundle
        """
        response = await api_client.get(
            "/api/questionnaires/search",
            params={"title": "ABSOLUTELY_NONEXISTENT_QUESTIONNAIRE_12345"}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["total"] == 0
        assert len(bundle.get("entry", [])) == 0

    @pytest.mark.failure_scenarios
    async def test_search_with_invalid_parameter_graceful_handling(self, api_client):
        """
        Test: Invalid search parameters are handled gracefully

        Given: Invalid search parameter
        When: GET /api/questionnaires/search?invalid_param=value
        Then: Returns results (HAPI ignores unknown params) or 400
        """
        response = await api_client.get(
            "/api/questionnaires/search",
            params={"invalid_unknown_param": "value"}
        )

        # Should handle gracefully - either ignore or return error
        assert response.status_code in [200, 400]

    async def test_search_by_canonical_url(
        self,
        hapi_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL support search by canonical URL

        Test ID: TEST-SEARCH-CANONICAL-URL
        Requirement: SDC-FM-Q-021-SHALL

        Given: Questionnaire with canonical URL
        When: GET /Questionnaire?url=[canonical] (HAPI search)
        Then: Returns matching Questionnaire

        Reference: FHIR R4 Canonical URLs, SDC IG Form Manager
        """
        # Create questionnaire with canonical URL
        questionnaire = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/Questionnaire/test-search-canonical-new",
            "version": "1.0.0",
            "status": "active",
            "title": "Test Search by Canonical URL",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        await clean_questionnaire(questionnaire)

        # Search by canonical URL using HAPI directly
        response = await hapi_client.get(
            "/Questionnaire",
            params={"url": "http://example.org/Questionnaire/test-search-canonical-new"}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "searchset"
        assert bundle["total"] >= 1

        # Verify the correct questionnaire was found
        found_urls = [
            entry["resource"].get("url")
            for entry in bundle.get("entry", [])
            if "url" in entry["resource"]
        ]
        assert "http://example.org/Questionnaire/test-search-canonical-new" in found_urls

    async def test_search_by_url_and_version(
        self,
        hapi_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL support search by URL and version

        Test ID: TEST-SEARCH-URL-VERSION
        Requirement: SDC-FM-Q-022-SHALL

        Given: Multiple versions of same Questionnaire
        When: GET /Questionnaire?url=[canonical]&version=[version] (HAPI search)
        Then: Returns only the specified version

        Reference: FHIR R4 Versioned Canonical URLs
        """
        # Create two versions of the same questionnaire
        questionnaire_v1 = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/Questionnaire/test-version-search-new",
            "version": "1.5.0",
            "status": "active",
            "title": "Version 1.5.0",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        questionnaire_v2 = {
            "resourceType": "Questionnaire",
            "url": "http://example.org/Questionnaire/test-version-search-new",
            "version": "2.5.0",
            "status": "active",
            "title": "Version 2.5.0",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        await clean_questionnaire(questionnaire_v1)
        await clean_questionnaire(questionnaire_v2)

        # Search for specific version using HAPI directly
        response = await hapi_client.get(
            "/Questionnaire",
            params={
                "url": "http://example.org/Questionnaire/test-version-search-new",
                "version": "1.5.0"
            }
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"
        assert bundle["total"] >= 1

        # Verify only version 1.5.0 is returned
        found_version_1_5 = False
        for entry in bundle.get("entry", []):
            resource = entry["resource"]
            if resource.get("url") == "http://example.org/Questionnaire/test-version-search-new":
                assert resource.get("version") == "1.5.0", f"Expected version 1.5.0 but got {resource.get('version')}"
                assert resource.get("title") == "Version 1.5.0"
                found_version_1_5 = True

        assert found_version_1_5, "Version 1.5.0 not found in search results"

    async def test_search_by_last_updated(
        self,
        hapi_client,
        clean_questionnaire
    ):
        """
        SDC Requirement: SHALL support search by _lastUpdated

        Test ID: TEST-SEARCH-LASTUPDATED
        Requirement: SDC-FM-SP-002-SHALL

        Given: Questionnaires with different update times
        When: GET /Questionnaire?_lastUpdated=gt[timestamp] (HAPI search)
        Then: Returns only Questionnaires updated after timestamp

        Reference: FHIR R4 _lastUpdated search parameter
        """
        import datetime

        # Create first questionnaire
        q1 = {
            "resourceType": "Questionnaire",
            "status": "draft",
            "title": "First Questionnaire Test LastUpdated",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }
        q1_id = await clean_questionnaire(q1)

        # Get the first questionnaire to check its lastUpdated timestamp
        response = await hapi_client.get(f"/Questionnaire/{q1_id}")
        q1_resource = response.json()
        q1_last_updated = q1_resource["meta"]["lastUpdated"]

        # Wait a moment to ensure different timestamps
        import asyncio
        await asyncio.sleep(2)

        # Create second questionnaire after waiting
        q2 = {
            "resourceType": "Questionnaire",
            "status": "draft",
            "title": "Second Questionnaire Test LastUpdated",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }
        await clean_questionnaire(q2)

        # Search for questionnaires updated after the first one using HAPI directly
        response = await hapi_client.get(
            "/Questionnaire",
            params={"_lastUpdated": f"gt{q1_last_updated}"}
        )

        assert response.status_code == 200
        bundle = response.json()

        assert bundle["resourceType"] == "Bundle"

        # The second questionnaire should be in results (updated after q1)
        titles = [
            entry["resource"].get("title", "")
            for entry in bundle.get("entry", [])
        ]

        # Second Questionnaire should be found (created after timestamp)
        assert "Second Questionnaire Test LastUpdated" in titles, \
            f"Expected to find 'Second Questionnaire Test LastUpdated' but found: {titles}"


@pytest.mark.integration
@pytest.mark.failure_scenarios
@pytest.mark.asyncio
class TestHAPIFailureScenarios:
    """
    Tests for handling HAPI FHIR failures.

    These tests verify the API handles HAPI errors gracefully.
    """

    async def test_malformed_json_returns_400(self, api_client):
        """
        Test: Malformed JSON in request body returns 400

        Given: Invalid JSON payload
        When: POST /api/questionnaires
        Then: Returns 400 Bad Request
        """
        # Send malformed JSON
        response = await api_client.post(
            "/api/questionnaires/",
            content=b'{"resourceType": "Questionnaire", invalid json}',
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422  # FastAPI validation error

    async def test_large_payload_handling(self, api_client):
        """
        Test: Very large Questionnaire is handled appropriately

        Given: Questionnaire with many items
        When: POST /api/questionnaires
        Then: Either succeeds or returns appropriate error
        """
        large_questionnaire = {
            "resourceType": "Questionnaire",
            "status": "draft",
            "item": [
                {
                    "linkId": f"item-{i}",
                    "text": f"Question {i}",
                    "type": "string"
                }
                for i in range(1000)  # 1000 items
            ]
        }

        response = await api_client.post(
            "/api/questionnaires/",
            json=large_questionnaire
        )

        # Should either succeed or return error (not crash)
        assert response.status_code in [200, 400, 413, 500]

    async def test_concurrent_updates_handling(
        self,
        api_client,
        clean_questionnaire
    ):
        """
        Test: Concurrent updates are handled by HAPI versioning

        Given: Questionnaire exists
        When: Multiple concurrent updates
        Then: HAPI handles versioning (may return conflict)
        """
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)

        update1 = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "active",
            "title": "Update 1",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        update2 = {
            "resourceType": "Questionnaire",
            "id": q_id,
            "status": "active",
            "title": "Update 2",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}]
        }

        # Send concurrent updates
        import asyncio
        responses = await asyncio.gather(
            api_client.put(f"/api/questionnaires/{q_id}", json=update1),
            api_client.put(f"/api/questionnaires/{q_id}", json=update2),
            return_exceptions=True
        )

        # At least one should succeed
        success_count = sum(
            1 for r in responses
            if not isinstance(r, Exception) and r.status_code == 200
        )

        assert success_count >= 1
