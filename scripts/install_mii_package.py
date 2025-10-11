"""
Install MII PRO package into HAPI FHIR at runtime using $install operation.

This script uses HAPI FHIR's built-in $install operation to load an IG package
without restarting the server.
"""
import asyncio
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FHIR_BASE = "http://localhost:8080/fhir"

# MII Packages available on Simplifier
MII_PACKAGES = {
    "mii-pro-2025": {
        "url": "https://packages.simplifier.net/de.medizininformatikinitiative.kerndatensatz.person/2025.0.0/package.tgz",
        "name": "de.medizininformatikinitiative.kerndatensatz.person",
        "version": "2025.0.0"
    },
    # Add more packages as needed
}


async def install_package_from_url(package_url: str, package_name: str):
    """
    Install a FHIR package from URL using $install operation.

    Args:
        package_url: URL to package.tgz file
        package_name: Name of the package for logging
    """
    logger.info(f"Installing {package_name} from {package_url}")

    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Use HAPI FHIR's $install operation
            # POST [base]/$install with package URL parameter
            response = await client.post(
                f"{FHIR_BASE}/$install",
                json={
                    "resourceType": "Parameters",
                    "parameter": [
                        {
                            "name": "packageUrl",
                            "valueString": package_url
                        }
                    ]
                },
                headers={"Content-Type": "application/fhir+json"}
            )

            if response.status_code in [200, 201]:
                logger.info(f"✓ Successfully installed {package_name}")
                logger.info(f"Response: {response.json()}")
                return True
            else:
                logger.error(f"✗ Failed to install {package_name}")
                logger.error(f"Status: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"✗ Error installing {package_name}: {e}")
            return False


async def check_hapi_ready():
    """Check if HAPI FHIR server is ready."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{FHIR_BASE}/metadata", timeout=5.0)
            return response.status_code == 200
        except:
            return False


async def verify_installation(resource_type: str, expected_count: int = None):
    """
    Verify package installation by checking if resources exist.

    Args:
        resource_type: Type of resource to check (e.g., "Questionnaire")
        expected_count: Optional expected minimum count
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{FHIR_BASE}/{resource_type}?_summary=count",
                headers={"Accept": "application/fhir+json"}
            )

            if response.status_code == 200:
                data = response.json()
                total = data.get("total", 0)
                logger.info(f"Found {total} {resource_type} resources")

                if expected_count and total < expected_count:
                    logger.warning(f"Expected at least {expected_count} resources, found {total}")
                    return False
                return True
            else:
                logger.error(f"Failed to verify {resource_type}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error verifying {resource_type}: {e}")
            return False


async def main():
    """Main installation routine."""
    logger.info("=" * 60)
    logger.info("MII Package Installer for HAPI FHIR")
    logger.info("=" * 60)

    # Check if HAPI FHIR is ready
    logger.info("Checking if HAPI FHIR is ready...")
    if not await check_hapi_ready():
        logger.error("HAPI FHIR server is not ready. Please start it first:")
        logger.error("  docker-compose up -d hapi-fhir")
        return

    logger.info("✓ HAPI FHIR is ready\n")

    # Install MII PRO package
    for package_id, package_info in MII_PACKAGES.items():
        logger.info(f"Installing {package_id}...")
        success = await install_package_from_url(
            package_info["url"],
            package_info["name"]
        )

        if success:
            logger.info(f"✓ {package_id} installed successfully\n")
        else:
            logger.error(f"✗ Failed to install {package_id}\n")
            continue

    # Verify installation
    logger.info("\nVerifying installation...")
    await asyncio.sleep(5)  # Give HAPI time to process

    await verify_installation("Questionnaire")
    await verify_installation("ValueSet")
    await verify_installation("CodeSystem")

    logger.info("\n" + "=" * 60)
    logger.info("Installation complete!")
    logger.info("=" * 60)
    logger.info("\nYou can now search for resources:")
    logger.info(f"  curl {FHIR_BASE}/Questionnaire")
    logger.info(f"  curl {FHIR_BASE}/ValueSet")


if __name__ == "__main__":
    asyncio.run(main())
