"""
PRO Library — content loading + manifest integrity tests

Verifies that the container correctly loads the PRO Library
(BIH-CEI provisional, 0.x line) alongside MII PRO at boot, and that
the CRMI asset-collection release manifest is internally consistent:
every relatedArtifact[] entry resolves to a present artefact at the
pinned version.

The tests exercise these CRMI release-primitive properties:
  - manifest is itself loaded (Library type=asset-collection)
  - every pinned canonical is resolvable
  - derivedFrom on derived Questionnaires preserves upstream attribution
  - CRMI Shareable / Computable capability extensions are present

Tests fail loudly if the container's IG installation is broken — these
are the integration analogue of the CI smoke test in
.github/workflows/build-and-publish.yml.
"""
import pytest
from tests.conftest import (
    PRO_LIBRARY_CANONICALS,
    PRO_LIBRARY_NAMESPACE,
    PRO_LIBRARY_VERSION,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestPROLibraryLoaded:
    """The container is supposed to load bih-cei.fhir.pro-library 0.1.0 at boot."""

    async def test_phq9_questionnaire_loaded(self, fhir_server):
        """PRO Library PHQ-9 v0.1.0 is resolvable by canonical + version."""
        canonical = PRO_LIBRARY_CANONICALS["phq_9"]
        response = await fhir_server.get(
            "/Questionnaire",
            params={"url": canonical, "version": PRO_LIBRARY_VERSION, "_summary": "true"},
        )
        response.raise_for_status()
        bundle = response.json()
        assert bundle.get("total", 0) == 1, (
            f"PRO Library PHQ-9 not loaded at {canonical}|{PRO_LIBRARY_VERSION}"
        )

    async def test_phq9_derivedFrom_preserved(self, fhir_server):
        """
        derivedFrom on the PRO Library PHQ-9 still points to MII PRO
        2026.3.0 — the derivation chain is not silently dropped during
        package installation.
        """
        canonical = PRO_LIBRARY_CANONICALS["phq_9"]
        response = await fhir_server.get(
            "/Questionnaire", params={"url": canonical, "version": PRO_LIBRARY_VERSION}
        )
        response.raise_for_status()
        q = response.json()["entry"][0]["resource"]

        derived_from = q.get("derivedFrom", [])
        assert any(
            "mii-qst-pro-phq-9" in df and "2026.3.0" in df
            for df in derived_from
        ), (
            f"derivedFrom does not preserve MII PRO 2026.3.0 upstream attribution: "
            f"{derived_from}"
        )

    async def test_phq9_capability_extensions(self, fhir_server):
        """CRMI Shareable + Computable capability tags are present."""
        canonical = PRO_LIBRARY_CANONICALS["phq_9"]
        response = await fhir_server.get(
            "/Questionnaire", params={"url": canonical, "version": PRO_LIBRARY_VERSION}
        )
        q = response.json()["entry"][0]["resource"]

        capabilities = {
            ext.get("valueCode")
            for ext in q.get("extension", [])
            if ext.get("url") == "http://hl7.org/fhir/StructureDefinition/cqf-knowledgeCapability"
        }
        assert "shareable" in capabilities, f"Missing 'shareable' tag — have {capabilities}"
        assert "computable" in capabilities, f"Missing 'computable' tag — have {capabilities}"


@pytest.mark.integration
@pytest.mark.asyncio
class TestReleaseManifestIntegrity:
    """
    The release manifest (Library type=asset-collection) is the CRMI release
    primitive. It MUST itself be loaded AND every relatedArtifact[] reference
    MUST resolve to a present artefact at the pinned version.

    A failing test here means a release was tagged with broken pinning —
    consumers pulling via $package?manifest=… would get an incomplete bundle.
    """

    async def test_manifest_loaded(self, fhir_server):
        canonical = PRO_LIBRARY_CANONICALS["release_manifest"]
        response = await fhir_server.get(
            "/Library",
            params={"url": canonical, "version": PRO_LIBRARY_VERSION, "_summary": "true"},
        )
        response.raise_for_status()
        bundle = response.json()
        assert bundle.get("total", 0) == 1, (
            f"Release manifest not loaded at {canonical}|{PRO_LIBRARY_VERSION}"
        )

    async def test_manifest_is_asset_collection(self, fhir_server):
        canonical = PRO_LIBRARY_CANONICALS["release_manifest"]
        response = await fhir_server.get(
            "/Library", params={"url": canonical, "version": PRO_LIBRARY_VERSION}
        )
        lib = response.json()["entry"][0]["resource"]

        types = [c.get("code") for c in lib.get("type", {}).get("coding", [])]
        assert "asset-collection" in types, (
            f"Manifest is not type=asset-collection (got {types}) — CRMI release "
            f"primitive must be an asset-collection Library"
        )

    async def test_every_related_artifact_resolves(self, fhir_server):
        """
        For each relatedArtifact[].resource in the manifest, fetch the canonical
        and assert exactly one matching resource exists at the pinned version.

        This is the manifest integrity guarantee: a consumer pulling via
        $package?manifest=… should never get a bundle with missing entries.
        """
        canonical = PRO_LIBRARY_CANONICALS["release_manifest"]
        response = await fhir_server.get(
            "/Library", params={"url": canonical, "version": PRO_LIBRARY_VERSION}
        )
        lib = response.json()["entry"][0]["resource"]

        related = lib.get("relatedArtifact", [])
        assert len(related) >= 1, "Manifest has no relatedArtifact entries — empty release?"

        # Resource types that do not carry a `version` element in R4 are
        # exempt from the |version pin requirement and are resolved by url
        # only. (R5 promotes ObservationDefinition to a versioned canonical;
        # this list shrinks on the R5 migration.)
        UNVERSIONED_IN_R4 = {"ObservationDefinition"}

        failures = []
        for ra in related:
            ref = ra.get("resource", "")
            canonical_url = ref.split("|", 1)[0]
            # Resource type sits at the path segment before the id
            # (e.g. https://.../pro-library/Questionnaire/phq-9 → Questionnaire)
            rtype = canonical_url.rsplit("/", 2)[-2]

            if rtype in UNVERSIONED_IN_R4:
                r = await fhir_server.get(
                    f"/{rtype}",
                    params={"url": canonical_url, "_summary": "true"},
                )
                total = r.json().get("total", 0) if r.status_code == 200 else -1
                if total < 1:
                    failures.append(
                        f"{rtype}: {canonical_url} not resolvable "
                        f"(status={r.status_code}, total={total})"
                    )
                continue

            if "|" not in ref:
                failures.append(f"relatedArtifact.resource missing |version: {ref}")
                continue

            _, version = ref.rsplit("|", 1)
            r = await fhir_server.get(
                f"/{rtype}",
                params={"url": canonical_url, "version": version, "_summary": "true"},
            )
            total = r.json().get("total", 0) if r.status_code == 200 else -1
            if total != 1:
                failures.append(
                    f"{rtype}: {canonical_url}|{version} not resolvable "
                    f"(status={r.status_code}, total={total})"
                )

        assert not failures, (
            "Release manifest has unresolvable relatedArtifact entries:\n  "
            + "\n  ".join(failures)
        )

    async def test_manifest_pins_a_pro_library_artefact(self, fhir_server):
        """
        Sanity: the manifest pins at least one PRO Library artefact (not just
        external references). Without this, the manifest is documentation, not
        a release composition.
        """
        canonical = PRO_LIBRARY_CANONICALS["release_manifest"]
        response = await fhir_server.get(
            "/Library", params={"url": canonical, "version": PRO_LIBRARY_VERSION}
        )
        lib = response.json()["entry"][0]["resource"]

        pro_lib_refs = [
            ra.get("resource", "")
            for ra in lib.get("relatedArtifact", [])
            if PRO_LIBRARY_NAMESPACE in ra.get("resource", "")
        ]
        assert len(pro_lib_refs) >= 1, (
            f"Manifest does not pin any PRO Library artefact (namespace "
            f"{PRO_LIBRARY_NAMESPACE}). Pinned: "
            f"{[ra.get('resource') for ra in lib.get('relatedArtifact', [])]}"
        )
