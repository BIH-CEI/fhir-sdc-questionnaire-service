"""HAPI CR's own Questionnaire/$package — documents why the sidecar exists.

$package is a CRMI operation (crmi-package): the first resource of every
package is an outcome manifest (Library asset-collection) carrying the
packaging messages. HAPI CR never creates that manifest when the packaged
artifact is not itself a Library, and then dereferences it:

    HAPI-0389 NullPointerException: Cannot invoke ILibraryAdapter.addCqfMessagesExtension(...)
    because PackageVisitor.getRootSpecificationLibrary(IBaseBundle) is null
      at org.opencds.cqf.fhir.cr.visitor.PackageVisitor.visit(PackageVisitor.java:276)

It fires whenever packaging produced a message (a ValueSet that includes a
whole CodeSystem without listing concepts, an id too long to normalise with
its version, an unresolvable versioned dependency) and no Library happens to
be in the bundle — i.e. for almost all MII PRO / PCOR-MII Questionnaires.
Unchanged in cqf-fhir-cr 4.9.0 … 4.13.0 and on clinical-reasoning master
(investigated 2026-10-19; no upstream issue found).

Strict xfail: the moment HAPI returns a CRMI-shaped package this test XPASSes
and fails the run — the signal to re-evaluate whether PackageService can
shrink to a thin proxy.
"""
import pytest

pytestmark = [pytest.mark.upstream, pytest.mark.asyncio]

CRMI_MANIFEST = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-manifestlibrary"


@pytest.mark.xfail(
    strict=True,
    reason="HAPI CR native $package: NPE at PackageVisitor.java:276 (no CRMI outcome "
           "manifest for non-Library roots) -> 500 on MII PRO. The sidecar's "
           "PackageService fills this gap. XPASS = re-evaluate the sidecar layer.",
)
async def test_hapi_native_package_is_crmi_conformant(fhir_server, pro_questionnaires):
    response = await fhir_server.get(f"/Questionnaire/{pro_questionnaires['qlq_c30']['id']}/$package")
    assert response.status_code == 200
    entries = response.json().get("entry", [])
    first = entries[0]["resource"] if entries else {}
    assert first.get("resourceType") == "Library", "CRMI: outcome manifest first"
    assert any(e["resource"]["resourceType"] == "ValueSet" for e in entries)
