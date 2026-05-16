# Artifact Metadata Policy

> **Status.** DRAFT v0 — captures decisions taken so far and the open questions that block first publication. Marked `TODO` items must be resolved before the first 1.0.0 release of the PRO library.

This document defines the metadata rules every canonical artefact (Questionnaire, ValueSet, CodeSystem, ConceptMap, Library, Provenance) published from the **PRO Library** must follow. It is the implementation contract behind the [`VISION.md`](VISION.md) "normative, versionable source" claim.

The PRO Library lives in a separate repository from the runtime form-manager (this repo). See VISION.md §Content/Distribution split.

---

## 1. Scope

Applies to every canonical resource the PRO Library publishes:

| Resource type | Why it's in scope |
|---|---|
| `Questionnaire` | The instruments themselves |
| `ValueSet` | Answer-option bindings (where externally bound) |
| `CodeSystem` | Domain-specific code systems (PRO-CTCAE, EORTC scales, etc.) |
| `ConceptMap` | Mappings from common non-FHIR capture conventions (REDCap, OpenClinica, …) into the canonical answer codes |
| `Library` | CRMI manifests pinning a release; CQL scoring libraries |
| `Provenance` | Per-release provenance records (who, when, from where) |

---

## 2. Canonical URL namespace

> **TODO — blocking.** The namespace is not yet decided. See VISION.md §3 for the decision matrix (BIH-CEI domain vs. consortium domain vs. neutral). Pick before the first publication — once published, canonicals are forever.

Working placeholder used in this document: `https://example.org/fhir/pro-library`. Replace globally before tagging 1.0.0.

URL pattern, once decided:

```
{namespace}/{ResourceType}/{instrument-shortname}-{purpose-suffix}

# Examples (placeholder namespace)
https://example.org/fhir/pro-library/Questionnaire/phq-9
https://example.org/fhir/pro-library/ValueSet/eortc-qlq-c30-scale-4pt
https://example.org/fhir/pro-library/CodeSystem/eortc-qlq-c30
https://example.org/fhir/pro-library/ConceptMap/phq-9-redcap-to-canonical
https://example.org/fhir/pro-library/Library/release-2026-q3      # release manifest
https://example.org/fhir/pro-library/Library/phq-9-scoring        # scoring CQL
```

Naming rules:
- Lowercase, kebab-case
- Instrument shortname matches the published instrument abbreviation (`phq-9`, `gad-7`, `eortc-qlq-c30`, `eq-5d-5l`, `pro-ctcae`, …)
- No version suffix in the URL path — versions are carried in `version`

---

## 3. Identifier strategy

Each artefact carries:

- `url` — canonical URL (immutable per artefact identity)
- `version` — SemVer string (see §4)
- `identifier[]` — at least one business identifier:
  - One `Identifier.system` for the PRO Library's internal stable ID
  - Optional further `Identifier`s linking to upstream registrations (DOI for the original instrument's publication, Simplifier package URL, …)

Rationale: `url` says *what it is*, `identifier` says *what it cross-references*.

---

## 4. Version policy — SemVer per instrument

Every artefact starts at **`1.0.0`** at first publication. Subsequent versions follow strict SemVer:

| Bump | Trigger (Questionnaire example) |
|---|---|
| **Major** (`X.0.0`) | Item structure changes that break existing QResponses (linkId changed, type changed, required-flag flipped); answer-coding system changed; canonical URL changed |
| **Minor** (`x.Y.0`) | Additive items (new `linkId`s); new translations added; new optional extensions; new `derivedFrom`/`relatedArtifact` |
| **Patch** (`x.y.Z`) | Display-text fixes; typos; non-semantic metadata corrections; documentation extensions |

Same pattern per ValueSet (Major when codes removed/changed, Minor when codes added, Patch when display fixed) and per CodeSystem (Major when concept hierarchy or codes changed, Minor when designations added, Patch when display fixed).

Library-level (release manifest) versioning is *also* SemVer, decoupled from per-instrument versions:
- Library Major bump when one or more bundled artefacts had a Major bump
- Library Minor bump when only Minor or Patch bumps occurred
- Library Patch reserved for manifest-only fixes (no artefact change)

Required field: `versionAlgorithm = "semver"` on every artefact (CRMI Shareable requires the algorithm to be declared).

---

## 5. Required metadata per CRMI tier

Every artefact in the PRO Library MUST satisfy at least **CRMI Shareable**. Most should also satisfy **CRMI Publishable**. The PRO Library's own profile (TODO §11) will codify these as conformance constraints.

### Shareable (SHALL)
- `url`
- `version`
- `versionAlgorithm` (= `"semver"`)
- `name` (machine-readable)
- `title` (human-readable)
- `status` (`active` for releases; `draft` only in pre-release branches; `retired` for deprecated)
- `description`

### Publishable (SHALL, additionally)
- `date` (last-changed timestamp)
- `publisher` (the PRO Library authority — fill in once §2 is decided)
- `contact[]` (at least one ContactDetail with email)
- `copyright` (license terms — see §9)

### Publishable (SHOULD, additionally)
- `useContext[]` (clinical context — typically the instrument's intended population)
- `purpose` (why this artefact exists in this collection)
- `approvalDate` (editorial board approval timestamp)
- `lastReviewDate`
- `effectivePeriod` (when the artefact is intended to be used)
- `author[]`, `editor[]`, `reviewer[]`, `endorser[]` (governance trail)

### Computable / Executable
Defined per resource type in subsequent profile work (TODO §11). For Questionnaire, the operational capability tags (`populatable`, `extractable`, `calculatable`) are carried in the `mii-ex-pro-questionnaire-capabilities` extension; the PRO Library will publish profiles that constrain which combinations qualify for each CRMI tier.

---

## 6. `derivedFrom` policy

The PRO Library starts as a **`derivedFrom` overlay** on MII PRO content (see VISION.md §Content/Distribution split for the strategic rationale).

Every Questionnaire that has an MII-PRO predecessor MUST declare:

```json
{
  "derivedFrom": [
    "https://www.medizininformatik-initiative.de/fhir/ext/modul-pro/Questionnaire/mii-qst-pro-phq-9|2026.3.0"
  ]
}
```

Versioned canonical (`|version`) form is required so that the derivation is reproducible — a future MII PRO 2026.4.0 doesn't silently change what we derived from.

Companion `Provenance` resource (see §8) records the editorial actions taken on top of the derivation: corrections, added translations, applied profile changes, contained-VS expansions.

Where there is no upstream (instruments the PRO Library originates), `derivedFrom` is omitted; provenance points to the original instrument owner directly.

---

## 7. `meta.profile` policy

Every published artefact carries `meta.profile` listing:
1. The PRO Library's own profile for the artefact type (e.g., `pro-library/StructureDefinition/cei-publishable-pro-questionnaire`) — TODO §11
2. The CRMI tier profile being claimed (e.g., `crmi-publishable-questionnaire`)
3. Any upstream profile still satisfied (e.g., the MII PRO Questionnaire profile if the derivation preserves conformance)

Order: most specific first.

---

## 8. `Provenance` policy

Each release of an artefact gets a companion `Provenance` resource:

```json
{
  "resourceType": "Provenance",
  "target": [{"reference": "Questionnaire/phq-9", "display": "phq-9 v1.0.0"}],
  "occurredDateTime": "2026-MM-DDTHH:MM:SSZ",
  "recorded": "2026-MM-DDTHH:MM:SSZ",
  "agent": [
    {"role": "author",   "who": {"reference": "Practitioner/..."}},
    {"role": "reviewer", "who": {"reference": "Practitioner/..."}},
    {"role": "approver", "who": {"reference": "Organization/cei-editorial-board"}}
  ],
  "entity": [
    {"role": "source", "what": {
      "reference": "https://www.medizininformatik-initiative.de/.../Questionnaire/mii-qst-pro-phq-9|2026.3.0"
    }},
    {"role": "source", "what": {
      "reference": "https://doi.org/10.1046/j.1525-1497.2001.016009606.x",
      "display": "Kroenke K, Spitzer RL, Williams JBW. PHQ-9. J Gen Intern Med 2001."
    }}
  ]
}
```

Required fields:
- `target` — the artefact + version
- `recorded`, `occurredDateTime`
- `agent[]` — at minimum author and approver
- `entity[]` — at minimum the upstream FHIR canonical (if `derivedFrom`) and the original instrument's bibliographic reference (DOI)

---

## 9. License / copyright policy

Per artefact, `copyright` MUST state:
1. The PRO Library's copyright on the FHIR encoding
2. The original instrument owner's terms (verbatim from the licensing document)
3. The licence required for downstream use, with version

Example pattern:

```text
FHIR encoding © 2026 BIH-CEI. Released under CC-BY-4.0.
Original instrument © 2001 Kroenke, Spitzer & Williams.
PHQ-9 is freely available for clinical and research use without permission;
attribution required (see PHQ Screeners site).
```

Licence-encumbered instruments (BDI-II, EORTC modules with translation rights, etc.) will be flagged with an additional `useContext` of `licenseRequired = true` so that distribution gating can reason about it. Detailed entitlement modeling lives outside this document (see VISION.md §3.2).

---

## 10. Language policy

> **TODO — needs decision.** Sync vs. independent translation versioning.

Two viable models:

| Model | Pro | Con |
|---|---|---|
| **Sync** — every release ships every supported language at the same version | Consumer pulls one bundle, gets all translations | Holds back releases when one translation is in review |
| **Independent** — each language has its own SemVer trajectory; release manifest pins per-language versions | Translations release when ready | Consumer must read manifest to know what's bundled |

Whichever wins:
- `Questionnaire.language` MUST be set on every released artefact
- Translations of `text`/`display` carried via the `translation` extension (`http://hl7.org/fhir/StructureDefinition/translation`), not duplicated resources
- Per-language designation extensions on `CodeSystem.concept[]` for code displays

---

## 11. Profile work (open)

> **TODO.** The PRO Library will need its own profile set, derived from CRMI base profiles + MII PRO profiles. At minimum:
>
> - `cei-shareable-pro-questionnaire`
> - `cei-publishable-pro-questionnaire`
> - `cei-executable-pro-questionnaire` (the formalisation of "MII PRO `populatable`+`extractable` ⇒ CRMI executable" — see VISION.md §6 RQ-Map)
>
> These are scaffolded in the new pro-library repo, not here.

---

## 12. Deprecation & retirement

- An artefact is **deprecated** when it should not be used in new work but remains valid for in-flight studies. `status = active`, plus a deprecation note in `description` and a `successor` extension pointing to the recommended replacement.
- An artefact is **retired** when no further use is endorsed. `status = retired`. Resource MUST remain resolvable for ≥ 2 years post-retirement (clinical-trial reproducibility floor).
- Retired artefacts continue to appear in release manifests for those 2 years; manifest entries are marked with a CRMI deprecation tag.

---

## 13. Open decisions (consolidated TODO list)

| # | Decision | Blocking |
|---|---|---|
| 1 | Canonical URL namespace + authority owner | First 1.0.0 publication |
| 2 | Sync vs. independent language versioning | First multi-language release |
| 3 | PRO Library profile set (`cei-*-pro-questionnaire`) | First profile-claiming publication |
| 4 | License-entitlement model (data structure for per-site/per-instrument permission) | First mTLS-gated distribution |
| 5 | Editorial board composition + signature procedure | Trust/signing infrastructure go-live |
| 6 | Default `useContext` taxonomy (PRO domain coding) | Useful filtering by indication |

---

## References

- [`VISION.md`](VISION.md) — strategic context for this policy
- [`FUTURE_IDEAS.md`](FUTURE_IDEAS.md) — adjacent capability ideas
- [CRMI v1.0.0 — Profiles](https://hl7.org/fhir/uv/crmi/profiles.html) — Shareable / Publishable / Computable / Executable definitions
- [SemVer 2.0.0](https://semver.org/) — versioning semantics
