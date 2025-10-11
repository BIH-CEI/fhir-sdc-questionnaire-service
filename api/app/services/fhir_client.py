"""FHIR client service for connecting to HAPI FHIR server."""
from fhirpy import AsyncFHIRClient
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class FHIRClientService:
    """Service for managing FHIR client connections."""

    def __init__(self):
        """Initialize FHIR client."""
        self.client = AsyncFHIRClient(
            url=settings.fhir_base_url,
            authorization=None,  # No auth for now
        )
        logger.info(f"FHIR client initialized with base URL: {settings.fhir_base_url}")

    async def search_resources(
        self,
        resource_type: str,
        **search_params
    ):
        """
        Search for FHIR resources.

        Args:
            resource_type: Type of FHIR resource (e.g., "Questionnaire")
            **search_params: Search parameters (e.g., status="active", title="diabetes")

        Returns:
            List of matching resources
        """
        try:
            resources = self.client.resources(resource_type)

            # Apply search parameters
            for key, value in search_params.items():
                if value is not None:
                    resources = resources.search(**{key: value})

            result = await resources.fetch_all()
            logger.info(f"Found {len(result)} {resource_type} resources")
            return result

        except Exception as e:
            logger.error(f"Error searching {resource_type}: {e}")
            raise

    async def get_resource(self, resource_type: str, resource_id: str):
        """
        Get a specific FHIR resource by ID.

        Args:
            resource_type: Type of FHIR resource
            resource_id: Resource ID

        Returns:
            FHIR resource
        """
        try:
            resource = await self.client.resources(resource_type).search(_id=resource_id).first()
            if not resource:
                logger.warning(f"{resource_type}/{resource_id} not found")
                return None

            logger.info(f"Retrieved {resource_type}/{resource_id}")
            return resource

        except Exception as e:
            logger.error(f"Error getting {resource_type}/{resource_id}: {e}")
            raise

    async def create_resource(self, resource_type: str, resource_data: dict):
        """
        Create a new FHIR resource.

        Args:
            resource_type: Type of FHIR resource
            resource_data: Resource data as dictionary

        Returns:
            Created resource with ID
        """
        try:
            resource = self.client.resource(resource_type, **resource_data)
            await resource.save()

            logger.info(f"Created {resource_type}/{resource.id}")
            return resource

        except Exception as e:
            logger.error(f"Error creating {resource_type}: {e}")
            raise

    async def update_resource(
        self,
        resource_type: str,
        resource_id: str,
        resource_data: dict
    ):
        """
        Update an existing FHIR resource.

        Args:
            resource_type: Type of FHIR resource
            resource_id: Resource ID
            resource_data: Updated resource data

        Returns:
            Updated resource
        """
        try:
            # Get existing resource
            resource = await self.get_resource(resource_type, resource_id)
            if not resource:
                raise ValueError(f"{resource_type}/{resource_id} not found")

            # Update fields
            for key, value in resource_data.items():
                setattr(resource, key, value)

            await resource.save()
            logger.info(f"Updated {resource_type}/{resource_id}")
            return resource

        except Exception as e:
            logger.error(f"Error updating {resource_type}/{resource_id}: {e}")
            raise

    async def delete_resource(self, resource_type: str, resource_id: str):
        """
        Delete a FHIR resource.

        Args:
            resource_type: Type of FHIR resource
            resource_id: Resource ID
        """
        try:
            resource = await self.get_resource(resource_type, resource_id)
            if not resource:
                raise ValueError(f"{resource_type}/{resource_id} not found")

            await resource.delete()
            logger.info(f"Deleted {resource_type}/{resource_id}")

        except Exception as e:
            logger.error(f"Error deleting {resource_type}/{resource_id}: {e}")
            raise

    async def execute_operation(
        self,
        resource_type: str,
        operation: str,
        resource_id: str = None,
        parameters: dict = None
    ):
        """
        Execute a FHIR operation (e.g., $expand, $validate-code).

        Args:
            resource_type: Type of FHIR resource
            operation: Operation name (without $)
            resource_id: Optional resource ID for instance-level operations
            parameters: Operation parameters

        Returns:
            Operation result
        """
        try:
            # Build operation URL
            if resource_id:
                url = f"{resource_type}/{resource_id}/${operation}"
            else:
                url = f"{resource_type}/${operation}"

            # Execute operation
            result = await self.client.execute(url, method="get", params=parameters)

            logger.info(f"Executed operation: {url}")
            return result

        except Exception as e:
            logger.error(f"Error executing operation {url}: {e}")
            raise


# Singleton instance
_fhir_client = None


def get_fhir_client() -> FHIRClientService:
    """Get singleton FHIR client instance."""
    global _fhir_client
    if _fhir_client is None:
        _fhir_client = FHIRClientService()
    return _fhir_client
