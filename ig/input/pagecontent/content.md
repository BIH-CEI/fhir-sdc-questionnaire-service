All content is baked into the server image at build time; the server needs no network access at boot.

| Content | Package | Notes |
|---------|---------|-------|
| SDC | `hl7.fhir.uv.sdc` 4.0.0 | Forms standard (profiles, extensions) |
| MII PRO | `de.medizininformatikinitiative.kerndatensatz.pros` 2027.0.0-ballot.1 | Current; **2026.7.0 retained** next to it |
| PRO Library | `bih-cei.fhir.pro-library` 0.1.4 | BIH-CEI Questionnaires with CQL scoring Libraries and a CRMI release manifest |
| PCOR-MII | `pcor-mii` 0.3.0 | Project IG on top of MII PRO |

The versions of a given image are recorded in its labels and in the image tags (`mii-pro-<version>`, `form-manager-<version>`).

### Several versions side by side

Older MII PRO versions stay installed as full content (profiles, terminology, Questionnaires), so QuestionnaireResponses that point to an older version keep resolving. Every canonical resource is resolvable by `url` and `version`:

    GET [base]/Questionnaire?url=https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire/mii-qst-pro-phq-9&version=2026.7.0

Without `version`, the highest active version is returned.

### Release manifests

The PRO Library publishes each release as a CRMI manifest (`Library` of type `asset-collection`) that pins the exact version of every artifact. A site can mirror a release by reading the manifest and fetching each `relatedArtifact` by `url|version`.

### Known content issues

- **MII PRO MIDOS2:** the Questionnaire references `mii-vs-pro-midos2-severity` and `-wellbeing`, which are missing from every published MII PRO version (the module's package build drops `draft` terminology). `$package` reports them as missing.
- **PCOR-MII:** the ImplementationGuide resource itself cannot be stored on HAPI; Questionnaires and terminology load normally.
