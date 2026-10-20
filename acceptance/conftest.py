"""Acceptance tests against a deployed Form Manager endpoint (via its mTLS proxy).

Configuration (environment):
  FM_ENDPOINT          https://host[:port]  (required; the FHIR base is <endpoint>/fhir)
  FM_CLIENT_CERT/KEY   an allowlisted client certificate and key (required)
  FM_SERVER_CA         CA bundle to verify the server certificate (optional;
                       default: system trust store)
  FM_UNLISTED_CERT/KEY a certificate from a trusted CA that is NOT allowlisted
                       (optional; enables the 403 checks)
  FM_EXPECT_MII_PRO_VERSION, FM_EXPECT_MII_PRO_RETAINED (space-separated),
  FM_EXPECT_PRO_LIBRARY_VERSION, FM_EXPECT_PCOR_MII_VERSION
                       expected content versions; default: read from the repo
                       checkout this suite lives in (the release being accepted).
                       An empty value skips that check.
  FM_LATENCY_P95       seconds (default 2.0); FM_LATENCY_SAMPLES (default 20)
  FM_EXPAND_SETTLE     seconds to wait for ValueSet pre-expansion after a fresh
                       start (default 90)

Every probe that is expected to be refused is built to be harmless even if the
rule were broken (invalid bodies, ids that do not exist, read-only system ops).
"""
import os
import re
import shutil
import ssl
import subprocess
from pathlib import Path
from typing import List, Optional

import httpx
import pytest

REPO = Path(__file__).resolve().parent.parent
FHIR_JSON = "application/fhir+json"

MII_PRO_BASE = "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro"
PRO_LIBRARY_BASE = "https://fhir.bih-charite.de/pro-library"
PCOR_BASE = "https://bih-cei.github.io/PCOR-MII"


def _env(name: str) -> Optional[str]:
    value = os.getenv(name)
    return value if value else None


def _dockerfile_arg(name: str) -> str:
    try:
        text = (REPO / "Dockerfile.form-manager").read_text()
    except OSError:
        return ""
    m = re.search(rf'^ARG {name}="?([^"\n]*)"?$', text, re.M)
    return m.group(1).strip() if m else ""


def _versions_env(name: str) -> str:
    try:
        text = (REPO / "versions.env").read_text()
    except OSError:
        return ""
    m = re.search(rf"^{name}=(\S*)", text, re.M)
    return m.group(1) if m else ""


def _expect(env_name: str, default: str) -> str:
    # An explicitly empty env var disables the check; unset uses the repo default.
    return os.environ[env_name] if env_name in os.environ else default


EXPECT_MII_PRO = _expect("FM_EXPECT_MII_PRO_VERSION", _dockerfile_arg("MII_PRO_VERSION"))
EXPECT_MII_PRO_RETAINED: List[str] = _expect(
    "FM_EXPECT_MII_PRO_RETAINED", _dockerfile_arg("MII_PRO_RETAINED_VERSIONS")
).split()
EXPECT_PRO_LIBRARY = _expect("FM_EXPECT_PRO_LIBRARY_VERSION", _versions_env("PRO_LIBRARY_VERSION"))
EXPECT_PCOR_MII = _expect("FM_EXPECT_PCOR_MII_VERSION", _versions_env("PCOR_MII_VERSION"))


def pytest_report_header(config):
    return [
        f"endpoint: {_env('FM_ENDPOINT')}",
        f"expected: MII PRO {EXPECT_MII_PRO or '-'} (retained: {' '.join(EXPECT_MII_PRO_RETAINED) or '-'}), "
        f"PRO Library {EXPECT_PRO_LIBRARY or '-'}, PCOR-MII {EXPECT_PCOR_MII or '-'}",
    ]


@pytest.fixture(scope="session")
def endpoint() -> str:
    ep = _env("FM_ENDPOINT")
    if not ep:
        pytest.exit("FM_ENDPOINT is not set (e.g. https://formmanager.example.org)", returncode=2)
    return ep.rstrip("/")


@pytest.fixture(scope="session")
def base(endpoint) -> str:
    return f"{endpoint}/fhir"


@pytest.fixture(scope="session")
def verify():
    return _env("FM_SERVER_CA")


def _client(server_ca, cert=None) -> httpx.Client:
    # One explicit SSLContext for server CA and client certificate: httpx 0.28
    # silently drops `cert=` when `verify` is a CA path.
    ctx = ssl.create_default_context(cafile=server_ca)
    if cert:
        ctx.load_cert_chain(*cert)
    return httpx.Client(
        verify=ctx,
        timeout=httpx.Timeout(60.0, connect=15.0),
        headers={"Accept": FHIR_JSON},
    )


@pytest.fixture(scope="session")
def client(verify):
    cert, key = _env("FM_CLIENT_CERT"), _env("FM_CLIENT_KEY")
    if not (cert and key):
        pytest.exit("FM_CLIENT_CERT and FM_CLIENT_KEY (allowlisted) are required", returncode=2)
    with _client(verify, (cert, key)) as c:
        yield c


@pytest.fixture(scope="session")
def anon_client(verify):
    with _client(verify) as c:
        yield c


@pytest.fixture(scope="session")
def rogue_client(verify, tmp_path_factory):
    """A self-signed client certificate no server should trust."""
    if not shutil.which("openssl"):
        pytest.skip("openssl not available to create a rogue certificate")
    d = tmp_path_factory.mktemp("rogue")
    key, crt = d / "rogue.key", d / "rogue.pem"
    subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
         "-subj", "/CN=acceptance-rogue", "-keyout", str(key), "-out", str(crt)],
        check=True, capture_output=True,
    )
    with _client(verify, (str(crt), str(key))) as c:
        yield c


@pytest.fixture(scope="session")
def unlisted_client(verify):
    cert, key = _env("FM_UNLISTED_CERT"), _env("FM_UNLISTED_KEY")
    if not (cert and key):
        pytest.skip("FM_UNLISTED_CERT/KEY not set (trusted but not allowlisted certificate)")
    with _client(verify, (cert, key)) as c:
        yield c


def outcome_code(response: httpx.Response) -> Optional[str]:
    """issue[0].code of an OperationOutcome body, else None."""
    try:
        body = response.json()
    except ValueError:
        return None
    if body.get("resourceType") != "OperationOutcome":
        return None
    issues = body.get("issue") or [{}]
    return issues[0].get("code")


def total(client: httpx.Client, url: str, params: dict) -> int:
    r = client.get(url, params={**params, "_summary": "count"})
    assert r.status_code == 200, f"{url} {params}: {r.status_code} {r.text[:200]}"
    return r.json().get("total", 0)
