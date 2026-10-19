"""LocalizationService — pure in-memory, no server."""
import copy

import pytest

from app.services.localization_service import LocalizationService

pytestmark = pytest.mark.unit

TRANSLATION_EXT = "http://hl7.org/fhir/StructureDefinition/translation"


def _translated(value: str, **translations: str) -> dict:
    """Build {field: value, _field: {extension: [...]}} halves for a field."""
    return {
        "extension": [
            {
                "url": TRANSLATION_EXT,
                "extension": [
                    {"url": "lang", "valueCode": lang},
                    {"url": "content", "valueString": content},
                ],
            }
            for lang, content in translations.items()
        ]
    }


MULTILINGUAL_Q = {
    "resourceType": "Questionnaire",
    "status": "active",
    "language": "en",
    "title": "Patient Health Questionnaire",
    "_title": _translated("", de="Fragebogen zur Patientengesundheit",
                          es="Cuestionario de salud del paciente"),
    "item": [
        {
            "linkId": "1",
            "type": "choice",
            "text": "Little interest or pleasure in doing things",
            "_text": _translated("", de="Wenig Interesse oder Freude an Tätigkeiten"),
            "answerOption": [
                {
                    "valueCoding": {
                        "code": "0",
                        "display": "Not at all",
                        "_display": _translated("", de="Überhaupt nicht"),
                    }
                }
            ],
        },
        {
            "linkId": "g",
            "type": "group",
            "text": "Group",
            "item": [
                {
                    "linkId": "g.1",
                    "type": "string",
                    "text": "Nested question",
                    "_text": _translated("", de="Verschachtelte Frage"),
                }
            ],
        },
    ],
}


@pytest.fixture
def svc():
    return LocalizationService()


def test_localize_replaces_text_and_strips_extensions(svc):
    out = svc.localize(MULTILINGUAL_Q, "de")

    assert out["title"] == "Fragebogen zur Patientengesundheit"
    assert "_title" not in out
    assert out["item"][0]["text"] == "Wenig Interesse oder Freude an Tätigkeiten"
    assert "_text" not in out["item"][0]
    assert out["language"] == "de"


def test_localize_recurses_into_nested_items(svc):
    out = svc.localize(MULTILINGUAL_Q, "de")
    nested = out["item"][1]["item"][0]
    assert nested["text"] == "Verschachtelte Frage"
    assert "_text" not in nested


def test_localize_translates_answer_option_display(svc):
    out = svc.localize(MULTILINGUAL_Q, "de")
    coding = out["item"][0]["answerOption"][0]["valueCoding"]
    assert coding["display"] == "Überhaupt nicht"
    assert "_display" not in coding


def test_localize_unknown_language_keeps_base_text_but_strips_extensions(svc):
    out = svc.localize(MULTILINGUAL_Q, "fr")
    assert out["title"] == "Patient Health Questionnaire"
    assert "_title" not in out
    assert out["language"] == "fr"


def test_localize_adds_localized_tag(svc):
    out = svc.localize(MULTILINGUAL_Q, "es")
    codes = [t.get("code") for t in out["meta"]["tag"]]
    assert "localized" in codes


def test_localize_does_not_mutate_input(svc):
    before = copy.deepcopy(MULTILINGUAL_Q)
    svc.localize(MULTILINGUAL_Q, "de")
    assert MULTILINGUAL_Q == before


def test_available_languages_includes_base_and_translations(svc):
    assert svc.get_available_languages(MULTILINGUAL_Q) == ["de", "en", "es"]


def test_available_languages_defaults_base_to_en(svc):
    q = {"resourceType": "Questionnaire", "title": "T",
         "_title": _translated("", de="T-de")}
    assert svc.get_available_languages(q) == ["de", "en"]


def test_validate_language_support(svc):
    assert svc.validate_language_support(MULTILINGUAL_Q, "de") is True
    assert svc.validate_language_support(MULTILINGUAL_Q, "fr") is False
