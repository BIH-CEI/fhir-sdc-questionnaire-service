"""Questionnaire CRUD and search through the sidecar."""
import asyncio

import pytest

from tests.fixtures.sample_resources import PHQ2_QUESTIONNAIRE, SIMPLE_TEXT_QUESTIONNAIRE

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestCreate:

    async def test_create_returns_resource_with_id(self, api_client, fhir_server):
        questionnaire = {
            "resourceType": "Questionnaire", "status": "draft",
            "title": "Test Questionnaire for Creation",
            "item": [{"linkId": "1", "text": "Sample question", "type": "string"}],
        }
        response = await api_client.post("/api/questionnaires/", json=questionnaire)
        try:
            assert response.status_code == 200
            created = response.json()
            assert created["resourceType"] == "Questionnaire"
            assert created["id"]
            assert created["title"] == questionnaire["title"]
            stored = await fhir_server.get(f"/Questionnaire/{created['id']}")
            assert stored.status_code == 200
        finally:
            if response.status_code == 200:
                await fhir_server.delete(f"/Questionnaire/{response.json()['id']}")

    async def test_create_wrong_resource_type_returns_400(self, api_client):
        response = await api_client.post("/api/questionnaires/", json={"resourceType": "Patient"})
        assert response.status_code == 400

    @pytest.mark.xfail(
        strict=True,
        reason="No request-time validation: HAPI validation is off by design and the "
               "sidecar does no schema pre-check, so a Questionnaire without the "
               "required `status` is stored (200). Flip when a pydantic/FHIR "
               "schema check is added to the sidecar.",
    )
    async def test_create_missing_required_field_is_rejected(self, api_client, fhir_server):
        response = await api_client.post(
            "/api/questionnaires/",
            json={"resourceType": "Questionnaire", "item": [{"linkId": "1", "text": "Q", "type": "string"}]},
        )
        if response.status_code == 200:
            await fhir_server.delete(f"/Questionnaire/{response.json()['id']}")
        assert response.status_code in (400, 422)

    async def test_create_large_questionnaire(self, api_client, fhir_server):
        large = {
            "resourceType": "Questionnaire", "status": "draft", "title": "Large",
            "item": [{"linkId": f"item-{i}", "text": f"Question {i}", "type": "string"} for i in range(1000)],
        }
        response = await api_client.post("/api/questionnaires/", json=large)
        try:
            assert response.status_code == 200
            assert len(response.json()["item"]) == 1000
        finally:
            if response.status_code == 200:
                await fhir_server.delete(f"/Questionnaire/{response.json()['id']}")


class TestRead:

    async def test_get_by_id(self, api_client, load_test_fixtures):
        phq2_id = load_test_fixtures["phq2_questionnaire_id"]
        response = await api_client.get(f"/api/questionnaires/{phq2_id}")
        assert response.status_code == 200
        assert response.json()["id"] == phq2_id
        assert response.json()["title"] == PHQ2_QUESTIONNAIRE["title"]

    async def test_get_unknown_id_returns_404(self, api_client):
        response = await api_client.get("/api/questionnaires/INVALID_ID_DOES_NOT_EXIST")
        assert response.status_code == 404


class TestUpdate:

    async def test_update_replaces_fields(self, api_client, clean_questionnaire):
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)
        updated = {
            "resourceType": "Questionnaire", "id": q_id, "status": "active", "title": "Updated Title",
            "item": [{"linkId": "1", "text": "Question", "type": "string"}],
        }
        response = await api_client.put(f"/api/questionnaires/{q_id}", json=updated)

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Updated Title"
        assert body["status"] == "active"
        assert len(body["item"]) == 1

    @pytest.mark.xfail(
        strict=True,
        reason="update_resource sets attributes one by one on the fhirpy resource, so a "
               "field omitted from the PUT body survives — not a FHIR replace. Open bead.",
    )
    async def test_update_removes_omitted_fields(self, api_client, clean_questionnaire):
        q_id = await clean_questionnaire({**SIMPLE_TEXT_QUESTIONNAIRE, "description": "to be removed"})
        response = await api_client.put(
            f"/api/questionnaires/{q_id}",
            json={"resourceType": "Questionnaire", "id": q_id, "status": "active",
                  "title": "No description", "item": SIMPLE_TEXT_QUESTIONNAIRE["item"]},
        )
        assert response.status_code == 200
        assert "description" not in response.json()

    async def test_update_unknown_id_returns_404(self, api_client):
        response = await api_client.put(
            "/api/questionnaires/NONEXISTENT_ID",
            json={"resourceType": "Questionnaire", "status": "active", "item": []},
        )
        assert response.status_code == 404

    async def test_update_id_mismatch_returns_400(self, api_client, clean_questionnaire):
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)
        response = await api_client.put(
            f"/api/questionnaires/{q_id}",
            json={"resourceType": "Questionnaire", "id": "different_id", "status": "active", "item": []},
        )
        assert response.status_code == 400

    async def test_concurrent_updates_at_least_one_succeeds(self, api_client, clean_questionnaire):
        q_id = await clean_questionnaire(SIMPLE_TEXT_QUESTIONNAIRE)
        body = lambda title: {"resourceType": "Questionnaire", "id": q_id, "status": "active",  # noqa: E731
                              "title": title, "item": [{"linkId": "1", "text": "Q", "type": "string"}]}
        responses = await asyncio.gather(
            api_client.put(f"/api/questionnaires/{q_id}", json=body("Update 1")),
            api_client.put(f"/api/questionnaires/{q_id}", json=body("Update 2")),
            return_exceptions=True,
        )
        statuses = [r.status_code for r in responses if not isinstance(r, Exception)]
        assert 200 in statuses, statuses


class TestDelete:

    async def test_delete_removes_resource(self, api_client, fhir_server):
        created = await fhir_server.post("/Questionnaire", json=SIMPLE_TEXT_QUESTIONNAIRE)
        q_id = created.json()["id"]

        response = await api_client.delete(f"/api/questionnaires/{q_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
        assert (await fhir_server.get(f"/Questionnaire/{q_id}")).status_code == 410

    async def test_delete_unknown_id_returns_404(self, api_client):
        response = await api_client.delete("/api/questionnaires/NONEXISTENT_ID_12345")
        assert response.status_code == 404


class TestSearch:

    async def test_search_by_status(self, api_client, load_test_fixtures):
        response = await api_client.get("/api/questionnaires/search", params={"status": "active"})
        assert response.status_code == 200
        bundle = response.json()
        assert bundle["type"] == "searchset"
        assert bundle["entry"]
        assert all(e["resource"]["status"] == "active" for e in bundle["entry"])

    async def test_search_by_title_finds_fixture(self, api_client, load_test_fixtures):
        response = await api_client.get("/api/questionnaires/search", params={"title": "PHQ-2 Depression"})
        assert response.status_code == 200
        titles = [e["resource"]["title"] for e in response.json()["entry"]]
        assert PHQ2_QUESTIONNAIRE["title"] in titles

    async def test_search_count_limits_page(self, api_client):
        response = await api_client.get("/api/questionnaires/search", params={"_count": 1})
        assert response.status_code == 200
        assert len(response.json()["entry"]) == 1

    @pytest.mark.xfail(
        strict=True,
        reason="search reports Bundle.total as the page length, not the server total "
               "(_count=1 → total=1). Open bead.",
    )
    async def test_search_total_is_server_total_not_page_length(self, api_client):
        all_ = (await api_client.get("/api/questionnaires/search", params={"_count": 100})).json()
        one = (await api_client.get("/api/questionnaires/search", params={"_count": 1})).json()
        assert len(all_["entry"]) > 1
        assert one["total"] == all_["total"]

    async def test_search_no_results(self, api_client):
        response = await api_client.get(
            "/api/questionnaires/search", params={"title": "ABSOLUTELY_NONEXISTENT_QUESTIONNAIRE_12345"}
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0
        assert response.json()["entry"] == []

    @pytest.mark.xfail(
        strict=True,
        reason="`q` maps to HAPI's _content, which needs hapi.fhir.advanced_lucene_indexing "
               "(off): HAPI-2566 → sidecar 500. Enable full-text indexing or drop `q`. Open bead.",
    )
    async def test_search_free_text(self, api_client, pro_questionnaires):
        """`q` maps to HAPI's _content."""
        response = await api_client.get("/api/questionnaires/search", params={"q": "PHQ-9", "_count": 50})
        assert response.status_code == 200
        urls = {e["resource"].get("url") for e in response.json()["entry"]}
        assert pro_questionnaires["phq_9"]["url"] in urls
