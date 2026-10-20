"""1 Transport: TLS version and server certificate."""
import os
import socket
import ssl
from urllib.parse import urlparse

import pytest

pytestmark = pytest.mark.transport


def _host_port(endpoint):
    u = urlparse(endpoint)
    return u.hostname, u.port or 443


def _context(max_version=None, client_cert=True):
    ctx = ssl.create_default_context(cafile=os.getenv("FM_SERVER_CA") or None)
    if max_version:
        ctx.minimum_version = ssl.TLSVersion.MINIMUM_SUPPORTED
        ctx.maximum_version = max_version
    if client_cert:
        ctx.load_cert_chain(os.environ["FM_CLIENT_CERT"], os.environ["FM_CLIENT_KEY"])
    return ctx


def test_negotiates_tls_1_2_or_newer(endpoint, client):
    host, port = _host_port(endpoint)
    with socket.create_connection((host, port), timeout=15) as sock:
        with _context().wrap_socket(sock, server_hostname=host) as tls:
            assert tls.version() in ("TLSv1.2", "TLSv1.3"), tls.version()


def test_refuses_tls_1_1(endpoint, client):
    host, port = _host_port(endpoint)
    try:
        ctx = _context(max_version=ssl.TLSVersion.TLSv1_1)
    except (ValueError, ssl.SSLError) as e:
        pytest.skip(f"local OpenSSL cannot offer TLS 1.1: {e}")
    try:
        with socket.create_connection((host, port), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as tls:
                pytest.fail(f"server accepted {tls.version()}")
    except ssl.SSLError as e:
        if "NO_PROTOCOLS_AVAILABLE" in str(e).upper() or "NO PROTOCOLS AVAILABLE" in str(e).upper():
            pytest.skip("local OpenSSL refuses to offer TLS 1.1 at all")
        # handshake refused by the server: expected


def test_server_certificate_is_valid_for_the_host(base, client):
    """httpx verifies chain and hostname (against FM_SERVER_CA or the system store)."""
    r = client.get(f"{base}/metadata")
    assert r.status_code == 200
