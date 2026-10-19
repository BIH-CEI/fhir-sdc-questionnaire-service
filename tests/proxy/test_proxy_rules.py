"""Proxy component test: the real proxy image in front of a dummy backend.

Setup -> request -> expect accept/reject -> breakdown, in seconds, without
HAPI, database or content. The dummy backend answers every request with
"reached-backend", so a 401/403/405 can only come from the proxy, and a pass
through is visible in the body.

    python -m pytest tests/proxy -q        (needs Docker, pytest, httpx)
"""
import os
import socket
import ssl
import subprocess
import time
import uuid
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
PKI = ROOT / "deploy" / "mtls" / "test-pki"
IMAGE = os.getenv("PROXY_IMAGE", "fhir-sdc-proxy:local")
BACKEND_IMAGE = "hashicorp/http-echo:1.0"
REACHED = "reached-backend"


def sh(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout.strip()


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def proxy():
    # --- Setup: build the proxy image, start dummy backend + proxy (TEST-ONLY PKI)
    if not os.getenv("PROXY_IMAGE"):
        sh("docker", "build", "-q", "-f", str(ROOT / "Dockerfile.proxy"), "-t", IMAGE, str(ROOT))
    name, port = f"proxytest-{uuid.uuid4().hex[:8]}", free_port()
    sh("docker", "network", "create", name)
    try:
        sh("docker", "run", "-d", "--name", f"{name}-backend", "--network", name,
           "--network-alias", "backend", BACKEND_IMAGE, "-listen=:5678", f"-text={REACHED}")
        mounts = []
        for f in ("ca.pem", "server.pem", "server.key", "allowlist.map"):
            mounts += ["-v", f"{PKI / f}:/etc/nginx/mtls/{f}:ro"]
        sh("docker", "run", "-d", "--name", f"{name}-proxy", "--network", name,
           "-p", f"127.0.0.1:{port}:8443", "-e", "MTLS_ENV=test",
           "-e", "HAPI_UPSTREAM=backend:5678", "-e", "SIDECAR_UPSTREAM=backend:5678",
           *mounts, IMAGE)
        url = f"https://localhost:{port}"
        # Docker publishes the port before nginx listens: wait for a real
        # HTTP answer, not just an open socket.
        deadline = time.monotonic() + 30
        while True:
            try:
                with httpx.Client(verify=context()) as c:
                    c.get(f"{url}/fhir/metadata")
                break
            except httpx.HTTPError:
                if time.monotonic() > deadline:
                    raise RuntimeError(sh("docker", "logs", f"{name}-proxy"))
                time.sleep(0.5)
        yield url
    finally:
        # --- Breakdown
        subprocess.run(["docker", "rm", "-f", f"{name}-proxy", f"{name}-backend"], capture_output=True)
        subprocess.run(["docker", "network", "rm", name], capture_output=True)


def context(site="site-a", max_version=None, ciphers=None):
    ctx = ssl.create_default_context(cafile=str(PKI / "ca.pem"))
    if site:
        ctx.load_cert_chain(str(PKI / f"{site}.pem"), str(PKI / f"{site}.key"))
    if max_version:
        ctx.maximum_version = max_version
    if ciphers:
        ctx.set_ciphers(ciphers)
    return ctx


def get(url, method="GET", site="site-a", **kw):
    with httpx.Client(verify=context(site)) as c:
        return c.request(method, url, **kw)


# --- certificates and allowlist ------------------------------------------------

def test_no_certificate_is_rejected(proxy):
    r = get(f"{proxy}/fhir/metadata", site=None)
    assert r.status_code == 401 and REACHED not in r.text


def test_not_allowlisted_is_rejected(proxy):
    r = get(f"{proxy}/fhir/metadata", site="site-b")
    assert r.status_code == 403 and REACHED not in r.text


def test_allowlisted_read_passes_through(proxy):
    r = get(f"{proxy}/fhir/Questionnaire")
    assert r.text.strip() == REACHED


# --- read-only rules ------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("POST", "/fhir/Questionnaire"),
    ("PUT", "/fhir/Questionnaire/x"),
    ("DELETE", "/fhir/Questionnaire/x"),
    ("POST", "/fhir/"),
])
def test_writes_are_rejected(proxy, method, path):
    r = get(f"{proxy}{path}", method=method, json={"resourceType": "Questionnaire"})
    assert r.status_code == 405 and REACHED not in r.text


@pytest.mark.parametrize("path", [
    "/fhir/$reindex", "/fhir/%24reindex", "/fhir/QuestionnaireResponse",
    "/fhir/Patient/1", "/fhir/Questionnaire/x/$populate", "/fhir/swagger-ui/",
])
def test_blocked_paths(proxy, path):
    r = get(f"{proxy}{path}")
    assert r.status_code == 403 and REACHED not in r.text


def test_read_only_post_operation_passes_through(proxy):
    r = get(f"{proxy}/fhir/ValueSet/$expand", method="POST", json={"resourceType": "Parameters"})
    assert r.text.strip() == REACHED


# --- TLS policy (same as SU-TermServ) ---------------------------------------------

def test_tls13_accepted(proxy):
    with httpx.Client(verify=context()) as c:
        assert c.get(f"{proxy}/fhir/metadata").text.strip() == REACHED


def test_tls12_with_strong_suite_accepted(proxy):
    ctx = context(max_version=ssl.TLSVersion.TLSv1_2, ciphers="ECDHE-RSA-AES128-GCM-SHA256")
    with httpx.Client(verify=ctx) as c:
        assert c.get(f"{proxy}/fhir/metadata").text.strip() == REACHED


def test_tls12_with_cbc_suite_rejected(proxy):
    ctx = context(max_version=ssl.TLSVersion.TLSv1_2, ciphers="ECDHE-RSA-AES128-SHA")
    with pytest.raises(httpx.ConnectError):
        with httpx.Client(verify=ctx) as c:
            c.get(f"{proxy}/fhir/metadata")
