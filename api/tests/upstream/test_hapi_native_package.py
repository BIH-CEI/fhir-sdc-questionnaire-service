"""HAPI CR's own Questionnaire/$package — documents why the sidecar exists.

HAPI 8.4+ ships a QuestionnairePackageProvider. On MII PRO PHQ-9 it has
returned 500 since HAPI 8.4 / MII PRO 2026.3.0 (still on HAPI 8.12 /
2027.0.0-ballot.1). When it did return a Bundle (commit eeb3492) it was
type=transaction and omitted answerValueSet / CodeSystem / cqf-library
resolution. Strict xfail: the moment HAPI returns an SDC-shaped collection
Bundle this test XPASSes and fails the run, which is the signal to
re-evaluate whether PackageService can shrink to a thin proxy.
"""
import pytest

pytestmark = [pytest.mark.upstream, pytest.mark.asyncio]


@pytest.mark.xfail(
    strict=True,
    reason="HAPI CR native $package: 500 on MII PRO PHQ-9, and when it worked it "
           "returned a transaction Bundle without terminology — the sidecar's "
           "PackageService fills this gap. XPASS = re-evaluate the sidecar layer.",
)
async def test_hapi_native_package_is_sdc_conformant(fhir_server, pro_questionnaires):
    response = await fhir_server.get(f"/Questionnaire/{pro_questionnaires['qlq_c30']['id']}/$package")
    assert response.status_code == 200
    bundle = response.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle.get("type") == "collection"
    assert any(e["resource"]["resourceType"] == "ValueSet" for e in bundle.get("entry", []))
