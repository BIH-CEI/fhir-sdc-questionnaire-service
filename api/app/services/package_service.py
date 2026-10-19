"""Service for packaging Questionnaires with dependencies ($package).

$package is a CRMI operation (hl7.fhir.uv.crmi 2.0.0, OperationDefinition
crmi-package); SDC itself does not define one. CRMI requires that "the first
resource returned in the resulting package will be an outcome manifest" — a
Library of type asset-collection (profile crmi-manifestlibrary) that lists the
packaged artifact (composed-of) and its dependencies (depends-on) and carries
the packaging messages as a contained OperationOutcome (cqf-messages).
HAPI's native $package crashes exactly there for Questionnaires (it never
creates the manifest; see tests/upstream/test_hapi_native_package.py).
"""
from typing import Optional, List, Dict, Set
from datetime import datetime
import json
import logging
import httpx

logger = logging.getLogger(__name__)

# Constants
MAX_BUNDLE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_BUNDLE_ENTRIES = 100

CRMI_MANIFEST_PROFILE = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-manifestlibrary"
CQF_MESSAGES = "http://hl7.org/fhir/StructureDefinition/cqf-messages"
LIBRARY_TYPE_SYSTEM = "http://terminology.hl7.org/CodeSystem/library-type"


def canonical_of(resource: dict) -> str:
    """`url|version` of a canonical resource; falls back to a relative
    reference for artifacts without a url (e.g. a POSTed draft)."""
    url = resource.get("url")
    if not url:
        rid = resource.get("id")
        return f"{resource.get('resourceType')}/{rid}" if rid else resource.get("resourceType", "")
    return f"{url}|{resource['version']}" if resource.get("version") else url


def build_outcome_manifest(root: dict, references: List[tuple], warnings: List[Dict]) -> dict:
    """CRMI outcome manifest for a package of `root`.

    references: (canonical as referenced, resolved resource or None), in
    traversal order. A resolved dependency is recorded with the exact
    url|version that was packaged; an unresolved one as it was referenced.
    """
    related = [{
        "type": "composed-of",
        "display": root.get("title") or root.get("name"),
        "resource": canonical_of(root),
    }]
    for referenced, resolved in references:
        dep = {"type": "depends-on",
               "resource": canonical_of(resolved) if resolved else referenced}
        if resolved and (resolved.get("title") or resolved.get("name")):
            dep["display"] = resolved.get("title") or resolved.get("name")
        related.append(dep)

    manifest = {
        "resourceType": "Library",
        "id": "package-manifest",
        "meta": {"profile": [CRMI_MANIFEST_PROFILE]},
        "status": "active",
        "type": {"coding": [{"system": LIBRARY_TYPE_SYSTEM, "code": "asset-collection"}]},
        "title": f"Package of {root.get('title') or root.get('name') or canonical_of(root)}",
        "date": datetime.utcnow().isoformat() + "Z",
        "relatedArtifact": related,
    }
    if warnings:
        manifest["contained"] = [{
            "resourceType": "OperationOutcome",
            "id": "messages",
            "issue": [{"severity": w["severity"], "code": w["code"], "diagnostics": w["diagnostics"]}
                      for w in warnings],
        }]
        manifest["extension"] = [{"url": CQF_MESSAGES, "valueReference": {"reference": "#messages"}}]
    return manifest


def version_key(version: Optional[str]) -> tuple:
    """Sortable key for FHIR business versions.

    Numeric dotted parts compare numerically; a release ranks above its own
    pre-release ("2027.0.0" > "2027.0.0-ballot.1"); a missing version ranks
    lowest. Mirrors ver_key() in hapi-scripts/load-instance-resources.sh.
    """
    base, _, pre = (version or "").partition("-")
    nums = []
    for part in base.split("."):
        try:
            nums.append(int(part))
        except ValueError:
            nums.append(0)
    while len(nums) < 3:
        nums.append(0)
    return (tuple(nums[:3]), 0 if pre else 1, pre)


def pick_version(entries: List[dict], preferred_version: Optional[str] = None) -> Optional[dict]:
    """Choose one resource from a searchset of the same canonical.

    1. the exact `preferred_version` if present (an unversioned reference
       inside a package resolves to that package version's own copy);
    2. otherwise the highest version among status=active resources;
    3. otherwise the highest version overall.
    """
    resources = [e["resource"] for e in entries if isinstance(e.get("resource"), dict)]
    if not resources:
        return None
    if preferred_version:
        for r in resources:
            if r.get("version") == preferred_version:
                return r
    active = [r for r in resources if r.get("status") == "active"] or resources
    return max(active, key=lambda r: version_key(r.get("version")))


class DependencyResolver:
    """Resolves transitive dependencies for Questionnaire resources."""

    def __init__(self, package_service):
        """Initialize dependency resolver."""
        self.service = package_service
        self.processed_urls: Set[str] = set()
        self.warnings: List[Dict] = []
        # (canonical as referenced, resolved resource or None) for the manifest
        self.references: List[tuple] = []

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
        resource_type: str,
        preferred_version: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Fetch resource by canonical URL with version support.

        Args:
            canonical_url: URL like "http://example.org/ValueSet/abc" or
                          "http://example.org/ValueSet/abc|1.0.0"
            resource_type: FHIR resource type
            preferred_version: for an unversioned canonical, prefer this
                business version (the referencing Questionnaire's own), then
                fall back to the highest active version. Several versions of
                one package coexist on the server — see ARCHITECTURE.md
                "Version retention".

        Returns:
            Resource dict or None if not found
        """
        if "|" in canonical_url:
            url, version = canonical_url.split("|", 1)
            return await self.service.find_canonical(resource_type, url, version)
        return await self.service.find_canonical(
            resource_type, canonical_url, None, preferred_version=preferred_version
        )

    async def resolve_all_dependencies(
        self,
        questionnaire: dict
    ) -> List[dict]:
        """
        Resolve all dependencies recursively.

        Returns list of dependency resources (ValueSets, CodeSystems, Libraries, etc.)
        """
        all_resources = []
        # Unversioned references inside a package resolve to that package
        # version's own copy of the target.
        preferred = questionnaire.get("version")

        # Extract ValueSet references
        valueset_urls = self.extract_valueset_refs(questionnaire)
        logger.info(f"Found {len(valueset_urls)} ValueSet references")

        # Fetch ValueSets
        for url in valueset_urls:
            if url.startswith("#") or url in self.processed_urls:
                continue

            valueset = await self.fetch_canonical(url, "ValueSet", preferred)
            self.references.append((url, valueset))
            self.processed_urls.add(url)

            if not valueset:
                self.warnings.append({
                    "severity": "warning",
                    "code": "not-found",
                    "diagnostics": f"Referenced ValueSet not found: {url}"
                })
                continue

            all_resources.append(valueset)

            # Extract CodeSystems from ValueSet
            codesystem_urls = self.extract_codesystem_refs(valueset)

            for cs_url in codesystem_urls:
                if cs_url in self.processed_urls:
                    continue

                codesystem = await self.fetch_canonical(cs_url, "CodeSystem", preferred)
                self.references.append((cs_url, codesystem))
                self.processed_urls.add(cs_url)

                if codesystem:
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

            library = await self.fetch_canonical(url, "Library", preferred)
            self.references.append((url, library))
            self.processed_urls.add(url)

            if library:
                all_resources.append(library)

                # Check for nested library references
                nested_library_urls = self.extract_library_refs(library)
                for nested_url in nested_library_urls:
                    if nested_url not in self.processed_urls:
                        nested_library = await self.fetch_canonical(nested_url, "Library", preferred)
                        self.references.append((nested_url, nested_library))
                        self.processed_urls.add(nested_url)
                        if nested_library:
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

            structuremap = await self.fetch_canonical(url, "StructureMap", preferred)
            self.references.append((url, structuremap))
            self.processed_urls.add(url)

            if structuremap:
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
        # HAPI reuses cached search results for 60 s by default; a canonical
        # lookup right after a content publish would serve the stale list.
        # Cache-Control: no-cache makes HAPI bypass its search cache.
        self.http_client = httpx.AsyncClient(timeout=30.0, headers={"Cache-Control": "no-cache"})

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
        questionnaire = await self.find_canonical("Questionnaire", url, version)
        if not questionnaire:
            raise ValueError(
                f"Questionnaire with url '{url}'"
                + (f" version '{version}'" if version else "")
                + " not found"
            )

        return await self.build_bundle(questionnaire, include_dependencies)

    async def find_canonical(
        self,
        resource_type: str,
        url: str,
        version: Optional[str] = None,
        preferred_version: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Resolve a canonical URL on the server.

        With `version`: exact match. Without: all versions are fetched and
        `pick_version` chooses (preferred_version, else highest active
        version). Returns the resource or None.
        """
        params = {"url": url}
        if version:
            params["version"] = version
        else:
            params["_count"] = "100"
        result = await self.fetch_resource(f"/{resource_type}", params=params)
        if not result:
            return None
        # HAPI may return Bundle with total > 0 but no entry field
        return pick_version(result.get("entry", []), preferred_version)

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
        resolver = DependencyResolver(self)
        dependencies = (
            await resolver.resolve_all_dependencies(questionnaire) if include_dependencies else []
        )

        # CRMI: the outcome manifest comes first, then the packaged artifact
        # and its dependencies. Packaging messages live in the manifest.
        manifest = build_outcome_manifest(questionnaire, resolver.references, resolver.warnings)
        bundle_entries = [{"resource": manifest}, {"resource": questionnaire}]
        bundle_entries.extend([{"resource": dep} for dep in dependencies])

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

    async def close(self):
        """Close HTTP client connection."""
        await self.http_client.aclose()
