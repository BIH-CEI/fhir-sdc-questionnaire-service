# Vision: A Normative, Versionable Source of PROM Questionnaires

> **Status.** Strategic document. Substrate for a planned DFG proposal and the long-horizon roadmap that frames every tactical decision in this repository. Living doc — revise as the position evolves.
>
> **Predecessors.** [`REFERENCE_IMPLEMENTATION_PLAN.md`](REFERENCE_IMPLEMENTATION_PLAN.md) (tactical components view, partially superseded by the cleanup that removed workshop/mock components). [`FUTURE_IDEAS.md`](FUTURE_IDEAS.md) (orthogonal capability ideas — Syndication, client-spec direction).

---

## 1. Why this matters

Patient-Reported Outcome Measures (PROMs) are the most fragmented data class in clinical research today. Every site reimplements the same instruments — encoding PHQ-9, EORTC QLQ-C30, EQ-5D into local Questionnaire/CRF formats, re-translating, re-validating scoring rules, re-negotiating licences. The result is well documented: months of integration work per site, brittle inter-site comparability, and repeated psychometric mistakes that the original instrument authors fixed years ago.

The Medical Informatics Initiative (MII) PRO module ([Ammon et al. 2024 — *Bundesgesundheitsblatt* 67(6):656-667](https://doi.org/10.1007/s00103-024-03888-4); [PCOR-MII 2025](https://link.springer.com/article/10.1007/s41666-025-00187-8)) has produced FHIR profiles for the underlying data model and a first set of profiled `Questionnaire` resources for ~20 instruments. The infrastructure to *serve* this content normatively — versioned, license-aware, conformance-tested, distributable in multiple channels — is missing.

This repository proposes that infrastructure: a **CRMI-conformant national reference Form Manager** that acts as the single source of truth for the FHIR-encoded PROM catalogue, distributes it through standards-based channels, and gates access by licence in a verifiable way.

## 2. What "normative" means here

A normative source of canonical resources must satisfy four properties simultaneously. Dropping any one collapses the value proposition.

| Property | Definition |
|---|---|
| **Normative** | When two consumers disagree on the content of an instrument, the source is the referee — by mandate of the body that governs it, not by self-declaration. |
| **Versionable** | Every artefact has a clear version trajectory: predecessor/successor relations, deprecation policy, lifetime guarantees adequate for clinical-trial reproducibility (≥ 2 years post-deprecation typical). |
| **Source** | Primary distribution endpoint with a verifiable provenance chain back to the instrument owner, not a downstream mirror. |
| **Pluralistic** | Many PROMs (PROMIS, EORTC, EQ-5D, PHQ family, GAD-7, HADS, CES-D, BDI, DASS, K6, PRO-CTCAE …) under one consistent governance and distribution model. |

## 3. Architectural layers

Seven layers, ordered from political (hardest to change, most determinative) to technical (easiest to revise).

### 3.1 Governance
Who decides what is normative? An editorial board with representation from clinicians, methodologists, terminologists, and licence stakeholders. Submission/review/release process with explicit accountability. Versioning policy (when does a change warrant a major bump). Conflict-resolution procedure (e.g., upstream EORTC publishes v3.1 before German translation is reviewed). Without an institutional mandate this layer is missing — the technical artefact is then a high-quality reference implementation, not a normative source.

### 3.2 Licence architecture
PROM licences are heterogeneous: PROMIS is free, EORTC is academic-free with registration, BDI-II is paid per site. The source must:
- maintain a per-instrument licence registry,
- record per-consumer entitlement (which site is permitted what),
- gate distribution accordingly via verifiable consumer identity (mTLS client certificates),
- produce auditable delivery logs for compliance reporting.

### 3.3 Technical distribution
Multiple channels, identical content, deterministic equivalence:
- **Container image** (cold start; what this repo ships today)
- **REST + `$crmi-package`** (on-demand pull, mTLS-gated, manifest-routed)
- **Atom Syndication feed** (live updates; CRMI Distribution Channel #4)
- **FHIR Package / NPM tarball** (for integration in local SUSHI/IG-build pipelines)

A consumer pinning the same `(canonical, version, language, manifest)` from any channel must receive byte-identical artefacts.

### 3.4 Versioning & lifecycle
- `Questionnaire.version`, `versionAlgorithm` (CRMI Shareable requires the algorithm to be declared explicitly)
- `Questionnaire.replaces` and predecessor/successor extensions for supersession chains
- Per-release **CRMI manifest** (a `Library` that pins every Questionnaire/ValueSet/CodeSystem at a specific version) — this becomes the unit of release
- Deprecation policy: ≥ 2 years availability post-deprecation, with explicit `Questionnaire.status = retired` flag and continued resolvability
- Per-language versioning policy: synchronised across release vs. per-language independent (decision per instrument family)

### 3.5 Trust & provenance
- Signed FHIR resources (JWS) so consumers can verify origin without trusting transport
- `Provenance` resource per release: original instrument authors, FHIR encoders, reviewers, approvers, dates
- Reproducible release artefacts with published SHA-256 across all channels
- Public, immutable changelog
- Strict operational separation: signed releases ≠ live editing surface

### 3.6 Wissenschaftliche Bindung
Every released `Questionnaire` is the FHIR encoding of a psychometrically validated instrument. Three obligations follow:
- **Bibliographic anchoring** — original publication DOI, validation cohort references, per-language translation-validation references
- **Computable scoring** as CQL `Library` resources, testable against reference responses
- **Per-instrument test suite** — sample `QuestionnaireResponse`s with expected scores, traceable to the original instrument's validation paper
- **Psychometric metadata** in `useContext` / extensions where applicable (Cronbach-α, MID/MCID)

### 3.7 Standards alignment
The source claims conformance to a documented stack so that consumers can discover its capabilities without reading prose:
- **CRMI** Artifact Repository Service + Artifact Terminology Service CapabilityStatements (instantiates)
- **SDC** Form Manager CapabilityStatement
- **MII PRO** content profiles
- **CRMI** Atom Syndication for change broadcast
- **CQF** for computable scoring rules
- **OAuth 2.1 + mTLS** for the licence gate (additive to CRMI, not in CRMI scope)

## 4. Where we are vs. where we need to be

| Layer | Today | Required |
|---|---|---|
| Container with MII PRO baked in | ✅ shipped via `ghcr.io/BIH-CEI/fhir-sdc-form-manager` | ✅ |
| `$package` operational | ✅ SDC-flavored | ⚠️ + CRMI parameter aliases, manifest support |
| Validation infrastructure | ✅ smoke + SDC compliance + integration tests in CI | ⚠️ + per-instrument test suites + scoring tests |
| CRMI conformance claim | ❌ | Artifact Repository + Terminology Service CSs |
| Versioning policy | implicit (inherited from MII PRO) | ❌ explicit local policy needed |
| Licence gate (mTLS) | ❌ | needs build |
| Provenance + signatures | ❌ | needs build |
| Editorial governance | ❌ | needs political process |
| Syndication feed | ❌ idea captured | needs build |
| Per-instrument test suites | ❌ | needs build |
| Scoring CQL libraries | ❌ (PRO-CTCAE excepted) | needs build |
| Language-version policy | inherited | ⚠️ needs explicit articulation |
| Trust anchor / authority | ❌ no mandate | political process |

## 5. Research questions

The questions that distinguish this from "we built more software". Each is publishable in its own right and together form a coherent DFG work-package structure.

1. **RQ-Norm.** How can a CRMI-conformant Form Manager serve as a normative, versionable source for licence-encumbered PROM Questionnaires while supporting site-specific extension without compromising normativity?

2. **RQ-Map.** How can operation-specific capability extensions (e.g., MII PRO's `mii-ex-pro-questionnaire-capabilities` with `populatable`/`extractable`/`calculatable`/…) be formalised against CRMI's lifecycle tiers (Shareable / Publishable / Computable / Executable) using FHIR profiles, such that conformance can be machine-validated and discovered via CapabilityStatement?

3. **RQ-Distribution.** Which combinations of distribution channels (container, REST `$package`, Atom syndication, FHIR Package/NPM) satisfy which consumer scenarios (cold start, live update, on-demand pull, build integration), and how is byte-equivalence across channels enforced and tested?

4. **RQ-Composition.** How can sites locally extend a normative artefact (`Questionnaire.derivedFrom`, ValueSet `compose`, CodeSystem supplements) without violating the normativity of the upstream source, and how does CRMI `manifest`-based composition formalise the resulting site-specific bundles?

5. **RQ-Validity.** What test methodology guarantees scientific validity of FHIR-encoded scoring (CQL libraries) against the original instrument's published validation, including across translations and variants?

6. **RQ-Licence.** How can per-consumer licence entitlement be expressed declaratively (e.g., as a CRMI manifest per site) and enforced via mTLS-bound identity, producing auditable distribution evidence acceptable to instrument-owner licensors?

## 6. Methodological contributions

The proposal's claim of novelty rests on:

- **First documented operationalisation of CRMI for PROM content** — CRMI is HL7-normative since 2024 with no peer-reviewed implementation papers to date.
- **Profile-based formalisation of the operational-vs-lifecycle capability mapping** — closing a gap CRMI explicitly leaves open for `Questionnaire`.
- **Channel-equivalence test framework** — proving that container / REST / syndication / NPM emit identical artefacts is a non-trivial test architecture problem.
- **Reproducible scoring validation** — coupling published validation literature to executable CQL with traceable test cases is, to our knowledge, not formalised in the PROM literature.
- **Licence-gated distribution as a CRMI-additive layer** — documenting an integration pattern for IP-encumbered canonical resources that does not exist in CRMI today.

## 7. Evaluation strategy

- **Conformance test suite** — independent verification of any client implementation against published CapabilityStatements
- **Channel-equivalence test** — automated comparison of artefacts retrieved via every distribution channel for a fixed manifest
- **Scoring regression suite** — published validation responses scored by our CQL libraries must match the original literature within stated tolerances
- **Site-extension acceptance scenarios** — three documented site-extension patterns (derive, VS extend, CS supplement) demonstrably composable into a working consumer bundle
- **Audit-evidence generation** — the licence gate produces logs that a third-party licence-compliance auditor can verify

## 8. Relationship to existing infrastructure

- **MII** — the proposed source serves the PRO module produced by the MII PRO working group; aligns with the MII KDS architecture documented in [Ammon et al. 2024](https://doi.org/10.1007/s00103-024-03888-4); positioned within the Interoperability WG ecosystem
- **NUM** (Netzwerk Universitätsmedizin) — natural distribution surface for the licence-gated channel; PCOR-MII is a candidate first consumer
- **CRMI / SDC / CQF** (HL7 international) — adopted as the standards substrate; the proposal advances reference implementation and feedback into these IGs
- **BIH-CEI** — the natural editorial host given existing role in MII KDS module work and methodological focus
- **TMF e.V.** — possible governance partner for the editorial board structure
- **EHDS** (European Health Data Space) — alignment target for the licence-gated, audit-evidence-producing distribution channel

## 9. Boundaries — what this is *not*

- Not a new PROM authoring tool. Instruments are encoded externally; the source serves the encoded forms.
- Not a replacement for clinical trial data managers (REDCap, OpenClinica). The source supplies the canonical instrument; data capture happens at sites.
- Not a renderer or filler. Form Renderer / Form Filler are separate SDC roles; the source publishes the artefact, downstream tools render and fill.
- Not a terminology server in itself. It depends on a terminology service (centrally SU-TermServ; locally Ontoserver/HAPI) for VS expansion.
- Not a national IT-operations platform. Operational hosting needs separate funding and SLAs incompatible with research grants alone.

## 10. Roadmap (work-package outline)

Coarse, illustrative — the DFG proposal would refine these.

| WP | Theme | Deliverables |
|---|---|---|
| **WP1 — Governance & Method** | Editorial process, versioning policy, licence-registry model | Process documentation, stakeholder engagement, governance proposal |
| **WP2 — CRMI Conformance** | Profile-based capability-tier formalisation; CapabilityStatement instantiation | `cei-shareable/publishable/executable-pro-questionnaire` profiles, derived CS, conformance tests |
| **WP3 — Distribution Channels** | Container, REST, syndication, NPM with byte-equivalence | Atom feed implementation, manifest endpoint, channel-equivalence test framework |
| **WP4 — Licence Gate** | mTLS authentication, manifest-per-site, audit logs | Reference auth integration, audit-log schema, licence-compliance report generator |
| **WP5 — Trust & Provenance** | Signed releases, Provenance resources, reproducibility | Signing pipeline, Provenance generation, reproducibility test |
| **WP6 — Scientific Validation** | Scoring CQL libraries, per-instrument test suites | CQL library set, test suite, validation-paper traceability matrix |
| **WP7 — Site Extension Patterns** | Reference patterns for site-side adaptation | Documented patterns + reference site bundle |
| **WP8 — Reference Clients** | Dockerised SDC-role implementations + conformance tests | Form Renderer / Filler / Receiver containers, role conformance test suite |
| **WP9 — Evaluation & Dissemination** | Adoption studies, publication, IG feedback | Implementation studies at ≥ 3 MII sites, peer-reviewed publications, HL7 ballot comments |

## References

- Ammon D, Kurscheidt M, Buckow K, et al. *Arbeitsgruppe Interoperabilität: Kerndatensatz und Informationssysteme für Integration und Austausch von Daten in der Medizininformatik-Initiative.* Bundesgesundheitsblatt 67(6):656-667 (2024). [doi:10.1007/s00103-024-03888-4](https://doi.org/10.1007/s00103-024-03888-4)
- *Integrating the Patient Perspective into Healthcare and Real-World Evidence: PCOR-MII.* J Healthcare Informatics Research (2025). [Springer](https://link.springer.com/article/10.1007/s41666-025-00187-8)
- HL7 [Canonical Resource Management Infrastructure (CRMI) IG v1.0.0](https://hl7.org/fhir/uv/crmi/) — normative since 2024.
- HL7 [Structured Data Capture (SDC) IG v3.0.0](https://hl7.org/fhir/us/sdc/) and the [Form Manager CapabilityStatement](https://build.fhir.org/ig/HL7/sdc/CapabilityStatement-sdc-form-manager.html).
- HL7 [Clinical Quality Framework (CQF) Knowledge Capability extension](http://hl7.org/fhir/extensions/5.1.0/StructureDefinition-cqf-knowledgeCapability.html).
- MII PRO module — [Modul-PROs Implementation Guide](https://simplifier.net/medizininformatikinitiative-modulpro), version 2026.3.0 as bundled in this repository's container image.
