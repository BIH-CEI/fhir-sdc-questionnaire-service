#!/usr/bin/env python3
"""
Runtime ISiK Installation Script

This script installs ISiK dependencies (DE Basisprofile) first, then downloads
the ISiK package and uploads individual profiles to HAPI after the server has
fully started, avoiding the Hibernate Search initialization issue.

Installation order:
1. Wait for HAPI to be ready
2. Wait for Hibernate Search initialization (60s delay)
3. Install dependencies (de.basisprofil.r4 1.5.4) using $install-package
4. Download and extract ISiK 5.1.0 package
5. Upload ISiK StructureDefinitions individually (skipping problematic profiles)
"""

import json
import time
import requests
import sys
import os
from pathlib import Path
import tempfile
import tarfile

HAPI_BASE_URL = os.getenv("HAPI_BASE_URL", "http://localhost:8080/fhir")
ISIK_PACKAGE_NAME = "de.gematik.isik"
ISIK_VERSION = "5.1.0"
MAX_WAIT_SECONDS = 300
CHECK_INTERVAL = 5

# Installation strategy:
# Try installing ISiK directly with fetchDependencies=true first.
# If that fails, fall back to manual dependency installation + individual profile upload.
TRY_DIRECT_ISIK_INSTALL = True

# ISiK dependencies to install manually if direct install fails
DEPENDENCIES = [
    {"name": "de.basisprofil.r4", "version": "1.5.4"},
]

def wait_for_hapi():
    """Wait for HAPI FHIR to be ready"""
    print("Waiting for HAPI FHIR to be ready...")
    elapsed = 0
    while elapsed < MAX_WAIT_SECONDS:
        try:
            response = requests.get(f"{HAPI_BASE_URL}/metadata", timeout=5)
            if response.status_code == 200:
                print("✓ HAPI FHIR is ready!")
                return True
        except requests.exceptions.RequestException:
            pass

        print(f"  Waiting... ({elapsed}s / {MAX_WAIT_SECONDS}s)")
        time.sleep(CHECK_INTERVAL)
        elapsed += CHECK_INTERVAL

    print(f"ERROR: HAPI FHIR did not become ready within {MAX_WAIT_SECONDS} seconds")
    return False

def wait_for_hibernate_search():
    """Wait additional time for Hibernate Search to be fully initialized"""
    print("\nWaiting for Hibernate Search initialization...")
    wait_time = 60
    print(f"  Sleeping for {wait_time} seconds to ensure Hibernate Search is ready...")
    time.sleep(wait_time)
    print("✓ Hibernate Search should be initialized now")

def install_dependency_package(package_name, version):
    """Install a dependency package using HAPI's $install operation"""
    print(f"\nInstalling dependency: {package_name}#{version}...")

    # Create Parameters resource for $install-package operation
    params = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "name", "valueString": package_name},
            {"name": "version", "valueString": version},
            {"name": "installMode", "valueString": "STORE_AND_INSTALL"},
            {"name": "reloadExisting", "valueBoolean": False},
            {"name": "fetchDependencies", "valueBoolean": True}
        ]
    }

    try:
        response = requests.post(
            f"{HAPI_BASE_URL}/$install-package",
            json=params,
            headers={"Content-Type": "application/fhir+json"},
            timeout=120  # Package installation can take time
        )

        if response.status_code in [200, 201]:
            print(f"✓ Successfully installed {package_name}#{version}")
            return True
        else:
            print(f"✗ Failed to install {package_name}#{version}: HTTP {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False

    except Exception as e:
        print(f"✗ Error installing {package_name}#{version}: {e}")
        return False

def download_isik_package():
    """Download ISiK package from packages.fhir.org"""
    print(f"\nDownloading ISiK package {ISIK_VERSION}...")

    package_url = f"https://packages.fhir.org/{ISIK_PACKAGE_NAME}/{ISIK_VERSION}"

    try:
        response = requests.get(package_url, timeout=30)
        response.raise_for_status()

        # Save to temp file
        temp_dir = tempfile.mkdtemp()
        package_path = Path(temp_dir) / f"{ISIK_PACKAGE_NAME}-{ISIK_VERSION}.tgz"

        with open(package_path, 'wb') as f:
            f.write(response.content)

        print(f"✓ Downloaded package to {package_path}")
        return package_path

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to download ISiK package: {e}")
        return None

def extract_package(package_path):
    """Extract package contents"""
    print("\nExtracting package...")

    extract_dir = package_path.parent / "extracted"
    extract_dir.mkdir(exist_ok=True)

    try:
        with tarfile.open(package_path, 'r:gz') as tar:
            tar.extractall(extract_dir)

        print(f"✓ Extracted to {extract_dir}")
        return extract_dir

    except Exception as e:
        print(f"✗ Failed to extract package: {e}")
        return None

def upload_structure_definitions(extract_dir):
    """Upload StructureDefinitions one by one, skipping problematic ones"""
    print("\nUploading StructureDefinitions...")

    package_dir = extract_dir / "package"
    if not package_dir.exists():
        print(f"✗ Package directory not found: {package_dir}")
        return False

    # Find all StructureDefinition files
    sd_files = list(package_dir.glob("StructureDefinition-*.json"))

    if not sd_files:
        print("✗ No StructureDefinition files found")
        return False

    print(f"Found {len(sd_files)} StructureDefinition files")

    uploaded = 0
    skipped = 0
    failed = 0

    # List of known problematic profiles to skip
    SKIP_PROFILES = [
        "ISiKKoerperkerntemperatur",  # Known to cause Hibernate Search error
    ]

    for sd_file in sd_files:
        try:
            with open(sd_file, 'r') as f:
                resource = json.load(f)

            resource_id = resource.get('id', 'unknown')
            resource_name = resource.get('name', 'unknown')

            # Skip problematic profiles
            if any(skip in resource_name for skip in SKIP_PROFILES):
                print(f"  ⊘ Skipping {resource_name} (known to cause errors)")
                skipped += 1
                continue

            # Remove snapshot if present (to avoid triggering generation)
            if 'snapshot' in resource:
                del resource['snapshot']
                print(f"  → Removed snapshot from {resource_name}")

            # Upload to HAPI
            response = requests.put(
                f"{HAPI_BASE_URL}/StructureDefinition/{resource_id}",
                json=resource,
                headers={"Content-Type": "application/fhir+json"},
                timeout=30
            )

            if response.status_code in [200, 201]:
                print(f"  ✓ Uploaded {resource_name}")
                uploaded += 1
            else:
                print(f"  ✗ Failed to upload {resource_name}: HTTP {response.status_code}")
                failed += 1

        except Exception as e:
            print(f"  ✗ Error processing {sd_file.name}: {e}")
            failed += 1

    print(f"\nUpload Summary:")
    print(f"  ✓ Uploaded: {uploaded}")
    print(f"  ⊘ Skipped: {skipped}")
    print(f"  ✗ Failed: {failed}")

    return uploaded > 0

def main():
    """Main installation process"""
    print("=" * 50)
    print("ISiK Runtime Installation Script")
    print("=" * 50)
    print(f"HAPI URL: {HAPI_BASE_URL}")
    print(f"Package: {ISIK_PACKAGE_NAME}#{ISIK_VERSION}")
    print(f"Strategy: {'Direct install with dependencies' if TRY_DIRECT_ISIK_INSTALL else 'Manual dependency + profile upload'}")
    print()

    # Step 1: Wait for HAPI
    if not wait_for_hapi():
        return 1

    # Step 2: Wait for Hibernate Search
    wait_for_hibernate_search()

    # Step 3: Try direct ISiK installation with fetchDependencies=true
    if TRY_DIRECT_ISIK_INSTALL:
        print("\n" + "=" * 50)
        print("Attempting Direct ISiK Installation")
        print("(with fetchDependencies=true)")
        print("=" * 50)

        success = install_dependency_package(ISIK_PACKAGE_NAME, ISIK_VERSION)

        if success:
            print("\n" + "=" * 50)
            print("✓ ISiK installed successfully via direct installation!")
            print("=" * 50)
            return 0
        else:
            print("\n⚠ Direct installation failed. Falling back to manual installation...")

    # Fallback: Step 4 - Install dependencies manually
    if DEPENDENCIES:
        print("\n" + "=" * 50)
        print(f"Installing {len(DEPENDENCIES)} Dependencies Manually")
        print("=" * 50)

        for dep in DEPENDENCIES:
            success = install_dependency_package(dep["name"], dep["version"])
            if not success:
                print(f"\n⚠ Warning: Failed to install dependency {dep['name']}#{dep['version']}")
                print("  Continuing with ISiK installation anyway...")

        print("\n✓ Dependency installation phase complete")

    # Fallback: Step 5 - Download ISiK package
    package_path = download_isik_package()
    if not package_path:
        return 1

    # Fallback: Step 6 - Extract package
    extract_dir = extract_package(package_path)
    if not extract_dir:
        return 1

    # Fallback: Step 7 - Upload ISiK StructureDefinitions individually
    print("\n" + "=" * 50)
    print("Installing ISiK Profiles Individually")
    print("=" * 50)
    if not upload_structure_definitions(extract_dir):
        return 1

    print("\n" + "=" * 50)
    print("Installation complete!")
    print("=" * 50)

    return 0

if __name__ == "__main__":
    sys.exit(main())
