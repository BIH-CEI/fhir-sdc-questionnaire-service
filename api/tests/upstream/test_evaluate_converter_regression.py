# -*- coding: utf-8 -*-
"""Regressionstests um den Parameters-Converter-Befund (2026-10-04).

Hintergrund (ARCHITECTURE.md → "clinical-reasoning >= 4.9
Parameters-Converter"): Ab HAPI 8.12 (cqf-fhir-cql 4.9.0) scheitert
`Library/$evaluate` OHNE expression-Filter, sobald ein oeffentliches Define
eine Ressource mit Backbone-Kindern liefert — bei uns `MostRecentResponse`
(komplette QuestionnaireResponse):

    Could not resolve inner FHIR type: QuestionnaireResponseItemAnswerComponent

Die CQL-AUSWERTUNG war intakt; nur die Rueckkonvertierung des Ergebnisses in
die Parameters-Ressource brach. Upstream behoben in clinical-reasoning 4.12.0
(PR #1089); seit dem HAPI-Basisimage v8.12.0-2 (cqf-fhir-cr 4.13.0) ist der
Fix im Image. Der Stolperdraht hat am 2026-10-19 wie vorgesehen ausgeloest.

1. Der Sidecar-Workaround (expression= nur fuer die benoetigten Defines)
   haelt: $compute-and-extract funktioniert, obwohl die Library ein
   resource-wertiges oeffentliches Define traegt. Bleibt bewusst bestehen
   (spart die Serialisierung der kompletten QuestionnaireResponse).
2. Der gefilterte $evaluate liefert die angeforderten Skalar-Defines korrekt.
3. Regression: Der UNgefilterte $evaluate funktioniert (vorher strict-xfail-
   Stolperdraht). Faellt er wieder, ist der Converter-Bug zurueck — z.B. durch
   ein Downgrade des HAPI-Basisimages.
"""
import pytest

from tests.support.pro_library import (
    PHQ9_Q_ID,
    PHQ9_SCORING_LIBRARY_ID,
    compute_and_extract,
    phq9_qr,
    post_qr,
)

pytestmark = [pytest.mark.upstream, pytest.mark.asyncio]

SCALAR_DEFINES = ["PHQ9Severity", "PHQ9TotalScore", "PROMISDepressionTScore"]
CONVERTER_ERROR_FRAGMENT = "Could not resolve inner FHIR type"


async def _evaluate(fhir_server, subject_ref: str, expressions=None) -> dict:
    params = [("subject", subject_ref)]
    for e in expressions or []:
        params.append(("expression", e))
    r = await fhir_server.get(f"/Library/{PHQ9_SCORING_LIBRARY_ID}/$evaluate", params=params)
    r.raise_for_status()
    return r.json()


def _by_name(parameters: dict) -> dict:
    return {p.get("name"): p for p in parameters.get("parameter", [])}


def _has_converter_error(parameters: dict) -> bool:
    for p in parameters.get("parameter", []):
        issues = p.get("resource", {}).get("issue", [])
        if any(CONVERTER_ERROR_FRAGMENT in (i.get("diagnostics") or "") for i in issues):
            return True
    return False


async def test_compute_succeeds_despite_converter_breaking_public_define(api_client, fhir_server, test_subject):
    """Der eigentliche Workaround-Regressionstest, auf Verhaltensebene:
    phq-9-scoring traegt das OEFFENTLICHE, resource-wertige Define
    `MostRecentResponse`, an dem der >=4.9-Converter bricht. Der Sidecar muss
    trotzdem durchkommen, weil er nur die Skalar-Defines der
    `sdc-calculatedExpression`s anfordert."""
    await post_qr(fhir_server, phq9_qr(test_subject, raw=27))

    result = await compute_and_extract(api_client, PHQ9_Q_ID, test_subject)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"


async def test_filtered_evaluate_returns_requested_scalar_defines(fhir_server, test_subject):
    """$evaluate MIT expression-Filter: genau die angeforderten Defines,
    korrekte Werte, kein Converter-Fehlerparameter."""
    await post_qr(fhir_server, phq9_qr(test_subject, raw=0))

    params = await _evaluate(fhir_server, test_subject, SCALAR_DEFINES)
    assert not _has_converter_error(params), params

    named = _by_name(params)
    assert set(SCALAR_DEFINES) <= set(named), f"fehlende Defines: {named.keys()}"
    assert named["PHQ9TotalScore"].get("valueInteger") == 0
    assert named["PHQ9Severity"].get("valueString") == "minimal"
    assert named["PROMISDepressionTScore"].get("valueDecimal") == 37.4


async def test_unfiltered_evaluate_works(fhir_server, test_subject):
    """UNgefilterter $evaluate inkl. des resource-wertigen Defines
    `MostRecentResponse`: seit cqf-fhir-cr >= 4.12 ohne Converter-Fehler."""
    await post_qr(fhir_server, phq9_qr(test_subject, raw=5))

    params = await _evaluate(fhir_server, test_subject, expressions=None)
    assert not _has_converter_error(params), f"Converter-Fehler zurueck (CR < 4.12 im Image?): {params}"
    assert _by_name(params).get("PHQ9TotalScore", {}).get("valueInteger") == 5
