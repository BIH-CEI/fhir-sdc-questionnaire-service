"""6 Latency: simple p95 thresholds for typical reads."""
import os
import time

import pytest

from conftest import MII_PRO_BASE

pytestmark = pytest.mark.latency

P95 = float(os.getenv("FM_LATENCY_P95", "2.0"))
SAMPLES = int(os.getenv("FM_LATENCY_SAMPLES", "20"))


def _p95(fn) -> float:
    times = []
    for _ in range(SAMPLES):
        t = time.perf_counter()
        r = fn()
        times.append(time.perf_counter() - t)
        assert r.status_code == 200, r.text[:200]
    times.sort()
    return times[min(len(times) - 1, int(round(0.95 * (len(times) - 1))))]


@pytest.mark.parametrize("label,path,params", [
    ("metadata", "/metadata", {}),
    ("search by canonical", "/Questionnaire", {"url": f"{MII_PRO_BASE}/Questionnaire/mii-qst-pro-phq-9"}),
    ("expand", "/ValueSet/$expand", {"url": f"{MII_PRO_BASE}/ValueSet/mii-vs-pro-eortc-qlq-c30-scale-4pt"}),
])
def test_p95_latency(base, client, label, path, params):
    client.get(f"{base}{path}", params=params)  # warm-up
    p95 = _p95(lambda: client.get(f"{base}{path}", params=params))
    assert p95 <= P95, f"{label}: p95 {p95:.2f}s > {P95}s"
