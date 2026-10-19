"""$localize and $languages — sidecar end to end.

MII PRO content is monolingual (German, no translation extensions), so the
multilingual input is synthetic and uploaded per test.
"""
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

TRANSLATION_EXT = "http://hl7.org/fhir/StructureDefinition/translation"


def _tr(**translations):
    return {"extension": [
        {"url": TRANSLATION_EXT, "extension": [
            {"url": "lang", "valueCode": lang},
            {"url": "content", "valueString": content},
        ]} for lang, content in translations.items()
    ]}


def _multilingual_questionnaire(url_suffix: str) -> dict:
    return {
        "resourceType": "Questionnaire",
        "url": f"http://example.org/Questionnaire/localize-{url_suffix}",
        "version": "1.0.0",
        "status": "active",
        "language": "en",
        "title": "Patient Health Questionnaire",
        "_title": _tr(de="Fragebogen zur Patientengesundheit", es="Cuestionario de salud"),
        "item": [
            {
                "linkId": "1", "type": "string",
                "text": "How are you?",
                "_text": _tr(de="Wie geht es Ihnen?"),
            }
        ],
    }


async def test_localize_by_id(api_client, clean_questionnaire):
    q_id = await clean_questionnaire(_multilingual_questionnaire("by-id"))

    response = await api_client.get(f"/api/questionnaires/{q_id}/$localize", params={"language": "de"})

    assert response.status_code == 200
    q = response.json()
    assert q["resourceType"] == "Questionnaire"
    assert q["language"] == "de"
    assert q["title"] == "Fragebogen zur Patientengesundheit"
    assert q["item"][0]["text"] == "Wie geht es Ihnen?"
    assert "_title" not in q and "_text" not in q["item"][0]


async def test_localize_by_canonical_url_and_version(api_client, clean_questionnaire):
    q = _multilingual_questionnaire("by-url")
    await clean_questionnaire(q)

    response = await api_client.get(
        "/api/questionnaires/$localize",
        params={"url": q["url"], "version": q["version"], "language": "es"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Cuestionario de salud"


async def test_localize_provided_resource_is_not_persisted(api_client, fhir_server):
    q = _multilingual_questionnaire("post")

    response = await api_client.post("/api/questionnaires/$localize", params={"language": "de"}, json=q)

    assert response.status_code == 200
    assert response.json()["title"] == "Fragebogen zur Patientengesundheit"
    search = await fhir_server.get("/Questionnaire", params={"url": q["url"], "_summary": "count"})
    assert search.json().get("total", 0) == 0


async def test_localize_unknown_id_returns_404(api_client):
    response = await api_client.get("/api/questionnaires/NOPE_LOCALIZE/$localize", params={"language": "de"})
    assert response.status_code == 404


async def test_localize_unknown_url_returns_404(api_client):
    response = await api_client.get(
        "/api/questionnaires/$localize",
        params={"url": "http://example.org/Questionnaire/does-not-exist", "language": "de"},
    )
    assert response.status_code == 404


async def test_localize_post_rejects_non_questionnaire(api_client):
    response = await api_client.post(
        "/api/questionnaires/$localize", params={"language": "de"},
        json={"resourceType": "Patient"},
    )
    assert response.status_code == 422


async def test_localize_requires_language_parameter(api_client, clean_questionnaire):
    q_id = await clean_questionnaire(_multilingual_questionnaire("no-lang"))
    response = await api_client.get(f"/api/questionnaires/{q_id}/$localize")
    assert response.status_code == 422


async def test_languages_lists_base_and_translations(api_client, clean_questionnaire):
    q_id = await clean_questionnaire(_multilingual_questionnaire("langs"))

    response = await api_client.get(f"/api/questionnaires/{q_id}/$languages")

    assert response.status_code == 200
    params = response.json()
    assert params["resourceType"] == "Parameters"
    langs = sorted(p["valueCode"] for p in params["parameter"] if p["name"] == "language")
    assert langs == ["de", "en", "es"]


async def test_languages_and_localize_on_real_mii_pro_content(api_client, pro_questionnaires):
    """MII PRO PHQ-9 is German with translation extensions; $languages lists
    them and $localize strips every translation extension for a chosen one."""
    q_id = pro_questionnaires["phq_9"]["id"]
    response = await api_client.get(f"/api/questionnaires/{q_id}/$languages")
    assert response.status_code == 200
    langs = [p["valueCode"] for p in response.json()["parameter"]]
    assert "de" in langs
    assert len(langs) >= 2, f"expected translations on MII PRO PHQ-9, got {langs}"

    target = next(lang for lang in langs if lang != "de")
    localized = await api_client.get(f"/api/questionnaires/{q_id}/$localize", params={"language": target})
    assert localized.status_code == 200
    body = localized.json()
    assert body["language"] == target

    def _no_translation_ext(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key.startswith("_") and isinstance(value, dict) and "extension" in value:
                    assert not any("translation" in e.get("url", "") for e in value["extension"]), key
                _no_translation_ext(value)
        elif isinstance(node, list):
            for v in node:
                _no_translation_ext(v)

    _no_translation_ext(body["item"])


async def test_languages_unknown_id_returns_404(api_client):
    response = await api_client.get("/api/questionnaires/NOPE_LANGS/$languages")
    assert response.status_code == 404
