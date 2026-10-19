"""ScoringExtractService static helpers — pure functions, no server."""
import pytest

from app.services.scoring_extract_service import (
    EXT_CQF_LIBRARY,
    EXT_Q_UNIT,
    EXT_SDC_CALC,
    EXT_SDC_EXTRACT,
    ScoringExtractService as S,
)

pytestmark = pytest.mark.unit


# ─── _band_for_value ──────────────────────────────────────────────────────

def _band(low, high, code, category="absolute", condition=None):
    qi = {"category": category, "range": {}}
    if low is not None:
        qi["range"]["low"] = {"value": low}
    if high is not None:
        qi["range"]["high"] = {"value": high}
    if code is not None:
        qi["context"] = {"coding": [{"code": code}]}
    if condition:
        qi["condition"] = condition
    return qi


PHQ9_BANDS = [
    _band(0, 4, "minimal"),
    _band(5, 9, "mild"),
    _band(10, 14, "moderate"),
    _band(15, 19, "moderately-severe"),
    _band(20, 27, "severe"),
]


@pytest.mark.parametrize("value,expected", [
    (0, "minimal"), (4, "minimal"), (5, "mild"), (9, "mild"),
    (10, "moderate"), (14, "moderate"), (15, "moderately-severe"),
    (19, "moderately-severe"), (20, "severe"), (27, "severe"),
])
def test_band_boundaries_inclusive(value, expected):
    assert S._band_for_value(PHQ9_BANDS, value)["coding"][0]["code"] == expected


def test_band_out_of_range_returns_none():
    assert S._band_for_value(PHQ9_BANDS, 28) is None
    assert S._band_for_value(PHQ9_BANDS, -1) is None


def test_band_open_ended_ranges():
    bands = [_band(None, 10, "low"), _band(11, None, "high")]
    assert S._band_for_value(bands, -100)["coding"][0]["code"] == "low"
    assert S._band_for_value(bands, 1000)["coding"][0]["code"] == "high"


def test_band_ignores_non_absolute_categories():
    bands = [_band(0, 100, "ref", category="reference")]
    assert S._band_for_value(bands, 50) is None


def test_band_falls_back_to_condition_text():
    qi = _band(0, 10, None, condition="0-10 = fine")
    qi["context"] = {"text": "fine"}
    assert S._band_for_value([qi], 5) == {"text": "fine"}


def test_band_non_numeric_value_returns_none():
    assert S._band_for_value(PHQ9_BANDS, "n/a") is None
    assert S._band_for_value(PHQ9_BANDS, None) is None


def test_band_accepts_decimal_string_values():
    bands = [_band(59.9, 64.9, "moderate")]
    assert S._band_for_value(bands, "62.2")["coding"][0]["code"] == "moderate"


# ─── _resolve_scoring_library_id ──────────────────────────────────────────

@pytest.mark.parametrize("canonical,expected", [
    ("https://x.org/Library/phq-9-scoring", "phq-9-scoring"),
    ("https://x.org/Library/phq-9-scoring|0.1.4", "phq-9-scoring"),
    ("https://x.org/Library/phq-9-scoring/", "phq-9-scoring"),
])
def test_resolve_library_id(canonical, expected):
    q = {"extension": [{"url": EXT_CQF_LIBRARY, "valueCanonical": canonical}]}
    assert S._resolve_scoring_library_id(q) == expected


def test_resolve_library_id_absent():
    assert S._resolve_scoring_library_id({}) is None
    assert S._resolve_scoring_library_id({"extension": [{"url": "other"}]}) is None


# ─── _extract_flagged_items ───────────────────────────────────────────────

def _item(link, *, extract=True, lang="text/cql-identifier", expr="Total", code=True):
    ext = []
    if extract is not None:
        ext.append({"url": EXT_SDC_EXTRACT, "valueBoolean": extract})
    if expr is not None:
        ext.append({"url": EXT_SDC_CALC,
                    "valueExpression": {"language": lang, "expression": expr}})
    item = {"linkId": link, "type": "integer", "extension": ext}
    if code:
        item["code"] = [{"system": "http://loinc.org", "code": "44261-6"}]
    return item


def test_flagged_items_requires_extract_cql_and_code():
    q = {"item": [
        _item("ok"),
        _item("no-extract", extract=False),
        _item("fhirpath", lang="text/fhirpath"),
        _item("no-expr", expr=None),
        _item("no-code", code=False),
    ]}
    flagged = S._extract_flagged_items(q)
    assert [f["item"]["linkId"] for f in flagged] == ["ok"]
    assert flagged[0]["cql_expression"] == "Total"


def test_flagged_items_only_walks_top_level():
    """Documents current behaviour: nested items are not visited."""
    q = {"item": [{"linkId": "g", "type": "group", "item": [_item("nested")]}]}
    assert S._extract_flagged_items(q) == []


# ─── _unpack_parameters / _merge_locations / _get_unit ────────────────────

def test_unpack_parameters_takes_first_value_member():
    params = {"parameter": [
        {"name": "PHQ9TotalScore", "valueInteger": 7},
        {"name": "PHQ9Severity", "valueString": "mild"},
        {"name": "NoValue"},
    ]}
    assert S._unpack_parameters(params) == {"PHQ9TotalScore": 7, "PHQ9Severity": "mild"}


def test_merge_locations_assigns_ids_from_transaction_response():
    obs = [{"resourceType": "Observation"}, {"resourceType": "Observation"}]
    resp = {"entry": [
        {"response": {"location": "Observation/42/_history/1"}},
        {"response": {"location": "Observation/43/_history/1"}},
    ]}
    merged = S._merge_locations(obs, resp)
    assert merged["type"] == "collection"
    assert [e["resource"]["id"] for e in merged["entry"]] == ["42", "43"]
    assert merged["entry"][0]["fullUrl"] == "Observation/42"


def test_merge_locations_tolerates_short_response():
    obs = [{"resourceType": "Observation"}]
    merged = S._merge_locations(obs, {"entry": []})
    assert "id" not in merged["entry"][0]["resource"]
    assert merged["entry"][0]["fullUrl"] is None


def test_get_unit_defaults_to_ucum_unity():
    assert S._get_unit({}) == "1"
    item = {"extension": [{"url": EXT_Q_UNIT, "valueCoding": {"code": "{score}"}}]}
    assert S._get_unit(item) == "{score}"
