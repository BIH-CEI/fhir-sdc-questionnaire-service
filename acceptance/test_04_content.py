"""4 Content: the expected packages and versions are served."""
import pytest

from conftest import (
    EXPECT_MII_PRO,
    EXPECT_MII_PRO_RETAINED,
    EXPECT_PCOR_MII,
    EXPECT_PRO_LIBRARY,
    MII_PRO_BASE,
    PCOR_BASE,
    PRO_LIBRARY_BASE,
    total,
)

pytestmark = pytest.mark.content

MII_PHQ9 = f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-phq-9"


def _need(value, what):
    if not value:
        pytest.skip(f"no expected {what} configured")


def test_capability_statement(base, client):
    cs = client.get(f"{base}/metadata").json()
    assert cs["fhirVersion"] == "4.0.1"


def test_mii_pro_current_version(base, client):
    _need(EXPECT_MII_PRO, "MII PRO version")
    assert total(client, f"{base}/Questionnaire", {"url": MII_PHQ9, "version": EXPECT_MII_PRO}) == 1


@pytest.mark.parametrize("version", EXPECT_MII_PRO_RETAINED or ["-"])
def test_mii_pro_retained_versions(base, client, version):
    _need(EXPECT_MII_PRO_RETAINED, "retained MII PRO versions")
    assert total(client, f"{base}/Questionnaire", {"url": MII_PHQ9, "version": version}) == 1


def test_mii_pro_terminology_installed(base, client):
    assert total(client, f"{base}/ValueSet", {"url:below": MII_PRO_BASE}) >= 10
    assert total(client, f"{base}/CodeSystem", {"url:below": MII_PRO_BASE}) >= 5


def test_pro_library(base, client):
    _need(EXPECT_PRO_LIBRARY, "PRO Library version")
    assert total(client, f"{base}/Questionnaire",
                 {"url": f"{PRO_LIBRARY_BASE}/Questionnaire/phq-9", "version": EXPECT_PRO_LIBRARY}) == 1
    manifest = f"{PRO_LIBRARY_BASE}/Library/release-{EXPECT_PRO_LIBRARY.replace('.', '-')}"
    r = client.get(f"{base}/Library", params={"url": manifest})
    entries = r.json().get("entry", [])
    assert entries, f"release manifest {manifest} not found"
    lib = entries[0]["resource"]
    assert lib["type"]["coding"][0]["code"] == "asset-collection"


def test_pcor_mii(base, client):
    _need(EXPECT_PCOR_MII, "PCOR-MII version")
    assert total(client, f"{base}/Questionnaire",
                 {"url": f"{PCOR_BASE}/Questionnaire/UKHDEDP", "version": EXPECT_PCOR_MII}) == 1
    assert total(client, f"{base}/Questionnaire", {"url:below": f"{PCOR_BASE}/Questionnaire/"}) >= 20
    assert total(client, f"{base}/CodeSystem",
                 {"url": f"{PCOR_BASE}/CodeSystem/pcor-item-dictionary"}) == 1
