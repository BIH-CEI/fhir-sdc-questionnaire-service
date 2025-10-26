"""Service for packaging Questionnaires with dependencies (SDC $package operation)."""
from typing import Optional, List, Dict, Set
from datetime import datetime
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Constants
MAX_BUNDLE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_BUNDLE_ENTRIES = 100


class DependencyResolver:
    """Resolves transitive dependencies for Questionnaire resources."""

    def __init__(self, package_service):
        """Initialize dependency resolver."""
        self.service = package_service
        self.processed_urls: Set[str] = set()
        self.warnings: List[Dict] = []

    def extract_valueset_refs(self, questionnaire: dict) -> List[str]:
        """
        Extract answerValueSet URLs from Questionnaire items.
        Recursively processes nested items.
        """
        urls = []

        def traverse(items):
            for item in items:
                if "answerValueSet" in item:
                    urls.append(item["answerValueSet"])

                if "item" in item:
                    traverse(item["item"])

        if "item" in questionnaire:
            traverse(questionnaire["item"])

        return urls

    def extract_codesystem_refs(self, valueset: dict) -> List[str]:
        """Extract CodeSystem URLs from ValueSet compose.include."""
        urls = []

        if "compose" in valueset:
            for include in valueset.get("compose", {}).get("include", []):
                if "system" in include:
                    urls.append(include["system"])

        return urls

    def extract_library_refs(self, resource: dict) -> List[str]:
        """Extract Library URLs from extensions."""
        urls = []

        if "extension" not in resource:
            return urls

        for ext in resource.get("extension", []):
            if ext.get("url") in [
                "http://hl7.org/fhir/StructureDefinition/cqf-library",
                "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-library"
            ]:
                if "valueCanonical" in ext:
                    urls.append(ext["valueCanonical"])
                elif "valueReference" in ext:
                    ref = ext["valueReference"].get("reference", "")
                    urls.append(ref)

        return urls

    def extract_structuremap_refs(self, questionnaire: dict) -> List[str]:
        """Extract StructureMap URLs from extensions."""
        urls = []

        if "extension" not in questionnaire:
            return urls

        for ext in questionnaire.get("extension", []):
            if ext.get("url") == "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-targetStructureMap":
                if "valueCanonical" in ext:
                    urls.append(ext["valueCanonical"])

        return urls

    async def fetch_canonical(
        self,
        canonical_url: str,
        resource_type: str
    ) -> Optional[dict]:
        """
        Fetch resource by canonical URL with version support.

        Args:
            canonical_url: URL like "http://example.org/ValueSet/abc" or
                          "http://example.org/ValueSet/abc|1.0.0"
            resource_type: FHIR resource type

        Returns:
            Resource dict or None if not found
        """
        # Parse version from canonical URL
        if "|" in canonical_url:
            url, version = canonical_url.split("|", 1)
            params = {"url": url, "version": version}
        else:
            url = canonical_url
            params = {
                "url": url,
                "status": "active",
                "_sort": "-_lastUpdated",
                "_count": "1"
            }

        # Fetch from HAPI
        result = await self.service.fetch_resource(f"/{resource_type}", params=params)

        if not result or result.get("total", 0) == 0:
            return None

        # HAPI may return Bundle with total > 0 but no entry field
        entries = result.get("entry", [])
        if not entries:
            return None

        return entries[0]["resource"]

    async def resolve_all_dependencies(
        self,
        questionnaire: dict
    ) -> List[dict]:
        """
        Resolve all dependencies recursively.

        Returns list of dependency resources (ValueSets, CodeSystems, Libraries, etc.)
        """
        all_resources = []

        # Extract ValueSet references
        valueset_urls = self.extract_valueset_refs(questionnaire)
        logger.info(f"Found {len(valueset_urls)} ValueSet references")

        # Fetch ValueSets
        for url in valueset_urls:
            if url in self.processed_urls:
                continue

            valueset = await self.fetch_canonical(url, "ValueSet")

            if not valueset:
                self.warnings.append({
                    "severity": "warning",
                    "code": "not-found",
                    "diagnostics": f"Referenced ValueSet not found: {url}"
                })
                continue

            self.processed_urls.add(url)
            all_resources.append(valueset)

            # Extract CodeSystems from ValueSet
            codesystem_urls = self.extract_codesystem_refs(valueset)

            for cs_url in codesystem_urls:
                if cs_url in self.processed_urls:
                    continue

                codesystem = await self.fetch_canonical(cs_url, "CodeSystem")

                if codesystem:
                    self.processed_urls.add(cs_url)
                    all_resources.append(codesystem)
                else:
                    # Don't warn about missing external CodeSystems (LOINC, SNOMED)
                    if not any(ext in cs_url for ext in ["loinc.org", "snomed.info"]):
                        self.warnings.append({
                            "severity": "information",
                            "code": "not-found",
                            "diagnostics": f"Referenced CodeSystem not found: {cs_url}"
                        })

        # Extract Library references
        library_urls = self.extract_library_refs(questionnaire)
        logger.info(f"Found {len(library_urls)} Library references")

        for url in library_urls:
            if url in self.processed_urls:
                continue

            library = await self.fetch_canonical(url, "Library")

            if library:
                self.processed_urls.add(url)
                all_resources.append(library)

                # Check for nested library references
                nested_library_urls = self.extract_library_refs(library)
                for nested_url in nested_library_urls:
                    if nested_url not in self.processed_urls:
                        nested_library = await self.fetch_canonical(nested_url, "Library")
                        if nested_library:
                            self.processed_urls.add(nested_url)
                            all_resources.append(nested_library)
            else:
                self.warnings.append({
                    "severity": "warning",
                    "code": "not-found",
                    "diagnostics": f"Referenced Library not found: {url}"
                })

        # Extract StructureMap references
        structuremap_urls = self.extract_structuremap_refs(questionnaire)
        logger.info(f"Found {len(structuremap_urls)} StructureMap references")

        for url in structuremap_urls:
            if url in self.processed_urls:
                continue

            structuremap = await self.fetch_canonical(url, "StructureMap")

            if structuremap:
                self.processed_urls.add(url)
                all_resources.append(structuremap)
            else:
                self.warnings.append({
                    "severity": "information",
                    "code": "not-found",
                    "diagnostics": f"Referenced StructureMap not found: {url}"
                })

        logger.info(f"Resolved {len(all_resources)} dependencies with {len(self.warnings)} warnings")
        return all_resources


class PackageService:
    """Service for packaging Questionnaires with dependencies."""

    def __init__(self, hapi_base_url: str):
        """Initialize package service."""
        self.hapi_base = hapi_base_url
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def package_by_id(
        self,
        questionnaire_id: str,
        include_dependencies: bool = True
    ) -> dict:
        """
        Package questionnaire by ID.

        Args:
            questionnaire_id: Questionnaire ID
            include_dependencies: Include transitive dependencies

        Returns:
            FHIR Bundle with Questionnaire and dependencies
        """
        # Fetch Questionnaire
        questionnaire = await self.fetch_resource(
            f"/Questionnaire/{questionnaire_id}"
        )

        if not questionnaire:
            raise ValueError(f"Questionnaire with id '{questionnaire_id}' not found")

        # Build bundle
        return await self.build_bundle(questionnaire, include_dependencies)

    async def package_by_url(
        self,
        url: str,
        version: Optional[str] = None,
        include_dependencies: bool = True
    ) -> dict:
        """
        Package questionnaire by canonical URL.

        Args:
            url: Canonical URL of Questionnaire
            version: Specific version (optional)
            include_dependencies: Include transitive dependencies

        Returns:
            FHIR Bundle with Questionnaire and dependencies
        """
        # Search for Questionnaire
        search_params = {"url": url}
        if version:
            search_params["version"] = version
        else:
            search_params["status"] = "active"
            search_params["_sort"] = "-_lastUpdated"
            search_params["_count"] = "1"

        search_result = await self.fetch_resource(
            "/Questionnaire",
            params=search_params
        )

        if not search_result or search_result.get("total", 0) == 0:
            raise ValueError(f"Questionnaire with url '{url}' not found")

        # HAPI may return Bundle with total > 0 but no entry field
        entries = search_result.get("entry", [])
        if not entries:
            raise ValueError(f"Questionnaire with url '{url}' not found")

        questionnaire = entries[0]["resource"]

        return await self.build_bundle(questionnaire, include_dependencies)

    async def package_resource(
        self,
        questionnaire: dict,
        include_dependencies: bool = True
    ) -> dict:
        """
        Package provided Questionnaire resource.

        Args:
            questionnaire: Questionnaire resource dict
            include_dependencies: Include transitive dependencies

        Returns:
            FHIR Bundle with Questionnaire and dependencies
        """
        # Validate resource type
        if questionnaire.get("resourceType") != "Questionnaire":
            raise ValueError("Resource must be of type 'Questionnaire'")

        return await self.build_bundle(questionnaire, include_dependencies)

    async def build_bundle(
        self,
        questionnaire: dict,
        include_dependencies: bool
    ) -> dict:
        """
        Build bundle with Questionnaire and dependencies.

        Args:
            questionnaire: Questionnaire resource dict
            include_dependencies: Whether to include dependencies

        Returns:
            FHIR Bundle resource
        """
        # Initialize bundle entries with Questionnaire first
        bundle_entries = [{"resource": questionnaire}]

        if not include_dependencies:
            # Return minimal bundle
            return self.create_bundle(bundle_entries)

        # Resolve dependencies
        resolver = DependencyResolver(self)
        dependencies = await resolver.resolve_all_dependencies(questionnaire)

        # Add dependencies to bundle
        bundle_entries.extend([{"resource": dep} for dep in dependencies])

        # Add warnings if any dependencies missing
        if resolver.warnings:
            bundle_entries.append({
                "resource": self.create_operation_outcome(resolver.warnings)
            })

        # Check size limits
        bundle = self.create_bundle(bundle_entries)
        bundle_size = len(json.dumps(bundle))

        if bundle_size > MAX_BUNDLE_SIZE_BYTES:
            raise ValueError(
                f"Bundle size ({bundle_size} bytes) exceeds maximum "
                f"({MAX_BUNDLE_SIZE_BYTES} bytes). Consider using "
                "include-dependencies=false or modular questionnaire design."
            )

        if len(bundle_entries) > MAX_BUNDLE_ENTRIES:
            raise ValueError(
                f"Bundle entry count ({len(bundle_entries)}) exceeds maximum "
                f"({MAX_BUNDLE_ENTRIES})"
            )

        logger.info(
            f"Created bundle with {len(bundle_entries)} entries, "
            f"size: {bundle_size} bytes"
        )

        return bundle

    async def fetch_resource(
        self,
        path: str,
        params: Optional[dict] = None
    ) -> Optional[dict]:
        """
        Fetch resource from HAPI FHIR.

        Args:
            path: Resource path (e.g., "/Questionnaire/123")
            params: Query parameters

        Returns:
            Resource dict or None if not found
        """
        url = f"{self.hapi_base}{path}"

        try:
            response = await self.http_client.get(url, params=params)

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def create_bundle(self, entries: list) -> dict:
        """
        Create FHIR Bundle resource.

        Args:
            entries: List of bundle entries

        Returns:
            FHIR Bundle resource
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        return {
            "resourceType": "Bundle",
            "id": f"package-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "type": "collection",
            "timestamp": timestamp,
            "meta": {
                "lastUpdated": timestamp,
                "tag": [
                    {
                        "system": "http://hl7.org/fhir/uv/sdc/CodeSystem/bundle-tag",
                        "code": "questionnaire-package",
                        "display": "Questionnaire Package"
                    }
                ]
            },
            "entry": entries
        }

    def create_operation_outcome(self, issues: list) -> dict:
        """
        Create OperationOutcome for warnings/errors.

        Args:
            issues: List of issue dicts with severity, code, diagnostics

        Returns:
            FHIR OperationOutcome resource
        """
        return {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": issue["severity"],
                    "code": issue["code"],
                    "diagnostics": issue["diagnostics"]
                }
                for issue in issues
            ]
        }

    async def close(self):
        """Close HTTP client connection."""
        await self.http_client.aclose()
