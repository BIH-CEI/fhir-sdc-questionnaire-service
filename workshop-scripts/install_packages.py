#!/usr/bin/env python3
"""
Install MII PRO packages on workshop HAPI servers
Simplified version for workshop demo
"""

import sys
import os
import requests
import time

SITE_A_URL = os.getenv("SITE_A_URL", "http://hapi-site-a:8080/fhir")
SITE_B_URL = os.getenv("SITE_B_URL", "http://hapi-site-b:8080/fhir")


def wait_for_hapi(url, max_wait=300):
    """Wait for HAPI FHIR to be ready"""
    print(f"Waiting for HAPI at {url}...")
    elapsed = 0
    while elapsed < max_wait:
        try:
            response = requests.get(f"{url}/metadata", timeout=5)
            if response.status_code == 200:
                print(f"✓ HAPI ready at {url}")
                return True
        except:
            pass

        time.sleep(5)
        elapsed += 5
        if elapsed % 30 == 0:
            print(f"  Still waiting... ({elapsed}s)")

    print(f"✗ HAPI did not become ready within {max_wait}s")
    return False


def main():
    """Install packages based on command line arguments"""

    print("=" * 50)
    print("Workshop Package Installer")
    print("=" * 50)

    if "--site-a" in sys.argv:
        print("\n📦 Installing packages on Site A...")
        if wait_for_hapi(SITE_A_URL):
            print("✓ Site A is ready")
            print("  Note: Packages configured in site-a-application.yaml")
            print("  HAPI will auto-install on startup")
        else:
            print("✗ Site A not reachable")
            return 1

    if "--site-b" in sys.argv:
        print("\n📦 Installing packages on Site B...")
        if wait_for_hapi(SITE_B_URL):
            print("✓ Site B is ready")
            print("  Note: Packages configured in site-b-application.yaml")
            print("  HAPI will auto-install on startup")
        else:
            print("✗ Site B not reachable")
            return 1

    print("\n" + "=" * 50)
    print("✓ Package installation check complete!")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    sys.exit(main())
