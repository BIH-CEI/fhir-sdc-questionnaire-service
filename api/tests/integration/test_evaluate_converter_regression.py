# -*- coding: utf-8 -*-
"""Regressionstests um den Parameters-Converter-Befund (2026-10-04).

Hintergrund (KNOWN_LIMITATIONS.md → "clinical-reasoning >= 4.9
Parameters-Converter"): Ab HAPI 8.12 (cqf-fhir-cql 4.9.0) scheitert
`Library/$evaluate` OHNE expression-Filter, sobald ein oeffentliches Define
eine Ressource mit Backbone-Kindern liefert — bei uns `MostRecentResponse`
(komplette QuestionnaireResponse):

    Could not resolve inner FHIR type: QuestionnaireResponseItemAnswerComponent

Die CQL-AUSWERTUNG ist intakt; nur die Rueckkonvertierung des Ergebnisses in
die Parameters-Ressource bricht. Drei Tests sichern das in beide Richtungen:

1. Der Sidecar-Workaround (expression= nur fuer die benoetigten Defines)
   haelt: $compute-and-extract funktioniert, OBWOHL die Library ein
   converter-brechendes oeffentliches Define traegt.
2. Der gefilterte $evaluate liefert die angeforderten Skalar-Defines korrekt.
3. STOLPERDRAHT (strict xfail): Der UNgefilterte $evaluate ist als
   known-failing markiert. Fixt Upstream den Converter, kippt der Test auf
   XPASS und schlaegt wegen strict=True FEHL — das ist Absicht: Dann sind
   KNOWN_LIMITATIONS zu aktualisieren, der expression-Filter wird optional,
   und die private-define-Hygiene (pro-library 0.2.0) ist neu zu bewerten.
"""
import pytest

from .test_compute_and_extract import (
    PHQ9_Q_ID,
    _compute_and_extract,
    _create_patient,
    _phq9_qr,
    _post_qr,
)

SCORING_LIBRARY_ID = "phq-9-scoring"
SCALAR_DEFINES = ["PHQ9Severity", "PHQ9TotalScore", "PROMISDepressionTScore"]
CONVERTER_ERROR_FRAGMENT = "Could not resolve inner FHIR type"


async def _evaluate(fhir_server, subject_ref: str, expressions=None) -> dict:
    params = [("subject", subject_ref)]
    for e in expressions or []:
        params.append(("expression", e))
    r = await fhir_server.get(
        f"/Library/{SCORING_LIBRARY_ID}/$evaluate", params=params
    )
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


@pytest.mark.asyncio
async def test_compute_succeeds_despite_converter_breaking_public_define(
    api_client, fhir_server
):
    """Der eigentliche Workaround-Regressionstest, auf Verhaltensebene:

    phq-9-scoring traegt (Stand 0.1.4) das OEFFENTLICHE, resource-wertige
    Define `MostRecentResponse`, an dem der >=4.9-Converter bricht. Der
    Sidecar muss trotzdem durchkommen, weil er nur die Skalar-Defines der
    `sdc-calculatedExpression`s anfordert. Bricht jemand den expression-
    Filter wieder heraus, wird dieser Test auf HAPI >= 8.12 rot.
    """
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=27))

    result = await _compute_and_extract(api_client, PHQ9_Q_ID, patient_ref)
    assert result["status"] == 200, f"non-200: {result['text'][:300]}"


@pytest.mark.asyncio
async def test_filtered_evaluate_returns_requested_scalar_defines(fhir_server):
    """$evaluate MIT expression-Filter: genau die angeforderten Defines,
    korrekte Werte, kein Converter-Fehlerparameter."""
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=0))

    params = await _evaluate(fhir_server, patient_ref, SCALAR_DEFINES)
    assert not _has_converter_error(params), params

    named = _by_name(params)
    assert set(SCALAR_DEFINES) <= set(named), f"fehlende Defines: {named.keys()}"
    assert named["PHQ9TotalScore"].get("valueInteger") == 0
    assert named["PHQ9Severity"].get("valueString") == "minimal"
    assert named["PROMISDepressionTScore"].get("valueDecimal") == 37.4


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason=(
        "clinical-reasoning >= 4.9 (HAPI >= 8.12): CqlFhirParametersConverter "
        "kann resource-wertige Defines mit Backbone-Kindern (MostRecentResponse) "
        "nicht in Parameters konvertieren — siehe KNOWN_LIMITATIONS.md. "
        "XPASS heisst: Upstream hat gefixt -> KNOWN_LIMITATIONS aktualisieren, "
        "expression-Filter-Zwang und private-define-Hygiene neu bewerten."
    ),
    strict=True,
)
async def test_unfiltered_evaluate_upstream_tripwire(fhir_server):
    """Stolperdraht: UNgefilterter $evaluate inkl. des resource-wertigen
    Defines. Erwartet heute den Converter-Fehler (xfail). Sobald er
    durchlaeuft, macht strict=True daraus einen harten Fehlschlag, damit
    der Upstream-Fix nicht unbemerkt bleibt."""
    patient_ref = await _create_patient(fhir_server)
    await _post_qr(fhir_server, _phq9_qr(patient_ref, raw=5))

    params = await _evaluate(fhir_server, patient_ref, expressions=None)
    assert not _has_converter_error(params), (
        f"Converter-Fehler (erwartet auf CR >= 4.9): {params}"
    )
    named = _by_name(params)
    assert named.get("PHQ9TotalScore", {}).get("valueInteger") == 5
