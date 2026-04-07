#!/usr/bin/env python3
"""
MII PRO Package Installer for HAPI FHIR Server

Installs MII PRO module dependencies and the PRO package itself
using HAPI's $install-package operation.
"""

import time
import requests
import os
import sys

HAPI_BASE_URL = os.getenv("HAPI_BASE_URL", "http://localhost:8095/fhir")
MAX_WAIT_SECONDS = 300
CHECK_INTERVAL = 5

PACKAGES = [
    # Dependencies first
    {"name": "hl7.fhir.r4.core",                              "version": "4.0.1"},
    {"name": "hl7.terminology",                                "version": "6.4.0"},
    {"name": "hl7.fhir.uv.sdc",                               "version": "3.0.0"},
    {"name": "de.medizininformatikinitiative.kerndatensatz.meta", "version": "2026.0.0"},
    # MII PRO
    {"name": "de.medizininformatikinitiative.kerndatensatz.pros", "version": "2026.0.1"},
]


def wait_for_hapi():
    print(f"Waiting for HAPI at {HAPI_BASE_URL}...")
    for _ in range(MAX_WAIT_SECONDS // CHECK_INTERVAL):
        try:
            r = requests.get(f"{HAPI_BASE_URL}/metadata", timeout=5)
            if r.status_code == 200:
                print("HAPI is ready.")
                return True
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL)
    print("ERROR: HAPI did not start in time.")
    return False


def install_package(name, version):
    print(f"Installing {name}#{version}...")
    payload = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "name",             "valueString": name},
            {"name": "version",          "valueString": version},
            {"name": "fetchDependencies","valueBoolean": False},
        ]
    }
    r = requests.post(
        f"{HAPI_BASE_URL}/$install-package",
        json=payload,
        headers={"Content-Type": "application/fhir+json"},
        timeout=120
    )
    if r.status_code in (200, 201):
        print(f"  ✅ {name}#{version} installed")
    else:
        print(f"  ⚠️  {name}#{version} → HTTP {r.status_code}: {r.text[:200]}")


if __name__ == "__main__":
    if not wait_for_hapi():
        sys.exit(1)

    # Extra delay for Hibernate Search initialization
    print("Waiting 60s for HAPI Hibernate Search initialization...")
    time.sleep(60)

    for pkg in PACKAGES:
        install_package(pkg["name"], pkg["version"])

    print("\n✅ MII PRO installation complete.")
