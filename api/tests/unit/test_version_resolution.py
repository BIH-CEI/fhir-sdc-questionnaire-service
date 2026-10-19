"""version_key / pick_version — the sidecar's canonical resolution policy."""
import pytest

from app.services.package_service import pick_version, version_key

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("higher,lower", [
    ("2027.0.0", "2027.0.0-ballot.1"),      # release beats its own pre-release
    ("2027.0.0-ballot.1", "2026.7.0"),      # newer line's pre-release beats older release
    ("2026.10.0", "2026.7.0"),              # numeric, not lexical
    ("2027.0.0-ballot.2", "2027.0.0-ballot.1"),
    ("0.1.4", "0.1.3"),
    ("1.0.0", None),                        # missing version ranks lowest
])
def test_version_key_ordering(higher, lower):
    assert version_key(higher) > version_key(lower)


def _entry(version, status="active"):
    return {"resource": {"resourceType": "ValueSet", "url": "http://x/VS", "version": version, "status": status}}


def test_pick_prefers_exact_preferred_version():
    entries = [_entry("2027.0.0-ballot.1"), _entry("2026.7.0")]
    assert pick_version(entries, preferred_version="2026.7.0")["version"] == "2026.7.0"


def test_pick_falls_back_to_highest_active_when_preferred_absent():
    entries = [_entry("2026.7.0"), _entry("2027.0.0-ballot.1")]
    assert pick_version(entries, preferred_version="2025.1.0")["version"] == "2027.0.0-ballot.1"


def test_pick_ignores_order_written():
    entries = [_entry("2027.0.0-ballot.1"), _entry("2026.7.0")]  # newer written first
    assert pick_version(entries)["version"] == "2027.0.0-ballot.1"


def test_pick_skips_retired_unless_nothing_else():
    entries = [_entry("2027.0.0", status="retired"), _entry("2026.7.0")]
    assert pick_version(entries)["version"] == "2026.7.0"
    assert pick_version([_entry("1.0.0", status="retired")])["version"] == "1.0.0"


def test_pick_empty_and_malformed():
    assert pick_version([]) is None
    assert pick_version([{"fullUrl": "x"}]) is None
