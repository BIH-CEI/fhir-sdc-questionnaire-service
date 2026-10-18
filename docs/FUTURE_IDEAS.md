# Future Ideas

Ideas the repo doesn't act on yet but should remember. Each entry: what, why, what would unblock it.

## Syndication as a third distribution channel

**Spec:** [FHIR Syndication IG](https://fhir.github.io/fhir-syndication-ig/) (Atom 1.0 + FHIR conventions, currently CI build / no STU).

**Idea.** Once a central Form Manager exists, expose a Syndication feed (Atom) alongside the container image, so MII sites can subscribe to instrument/ValueSet updates instead of waiting for a container rebuild.

Three-tier distribution would then be:

| Channel | Use case | Cadence |
|---------|----------|---------|
| Container image (today) | Cold start — site gets a reproducible baseline | Per release (months) |
| Syndication feed (future) | Live delta — site picks up new instruments / VS bumps | Per change (days) |
| `$package` over mTLS (future) | On-demand pull, gated by client cert / licence | Per request |

**Why this fits.** Aligns with the mTLS Form Manager vision: central catalogue, many consumers, per-site licensing. Syndication is the HL7-blessed pattern for that shape; the IG even defines the TLS + client-cert auth profile, so we'd avoid inventing our own subscription protocol.

**What would unblock it.**
- A central Form Manager actually exists (this repo today is the building block, not the deployed central instance).
- At least one MII site committed as a consumer (otherwise we're shipping a feed with no subscribers).
- Clarity on which resources go into the feed (Questionnaire? ValueSet? Library? all?).

**Implementation sketch (when the time comes).**
- FastAPI sidecar endpoint `/feed/atom.xml`, generated from `Questionnaire` / `ValueSet` resources in HAPI, ordered by `meta.lastUpdated`.
- Per-consumer filtering via mTLS-cert → licence lookup (same gate as `$package`).
- Atom `<entry>` per resource version; `<link>` points at the FHIR resource URL on this server.
- HAPI itself ships nothing for this — has to be sidecar.

**Open questions.**
- Push (WebSub) or pull-only? Syndication IG currently leans pull.
- Signed feeds? (Probably yes if licensing is enforced.)
- Granularity: one feed per consumer, or one feed with per-entry ACL?

**CRMI relationship.** CRMI canonises Atom-based syndication as Distribution Channel #4 (see `distribution.html`). Adopting Syndication is therefore not "yet another protocol" but the CRMI-native answer for live updates — same pattern, recognised tooling.

---

## Automated `lastReviewDate` triggered by literature watch

**Idea.** A scheduled job watches PubMed / Crossref / DOI registries for new publications relevant to each instrument we publish — new validated translations, updated reference values, psychometric updates, official errata. When a hit is detected, the artefact's `lastReviewDate` is **flagged as candidate for revision**, and an editorial board notification is generated. Review-date updates remain a human action (signed by the board), but the trigger and evidence collection are automated.

**Why this fits.** A normative source needs evidence-based maintenance, and the editorial board's bottleneck is *knowing what to look at*. Automating the watch decouples "we noticed there's new evidence" from "we decided how to act on it" — board time spent on judgement, not on triage.

**Concrete pieces.**
- Per-artefact watch config in the `pro-library` repo (e.g., a `watch.yaml` next to each Questionnaire's FSH source: PubMed query, Crossref author/keyword combo, DOI alerts, registry endpoints to poll).
- Scheduled GitHub Actions / cron job runs the queries, dedupes against last-seen state, opens an issue per new hit with extracted abstract + DOI link.
- Editorial review of the issue → if accepted as relevant, board signs off → `lastReviewDate` bumped, `Provenance` records the review event including the reference that triggered it.
- Negative review (not relevant) is also recorded → next watch pass won't re-flag the same paper.

**What would unblock it.**
- The `pro-library` repo exists with FSH-authored artefacts (per VISION.md §3.7a).
- A list of trustworthy literature sources per instrument (typically PubMed query, the original instrument publisher's update feed if any, Cochrane/PROQOLID for translations).
- An editorial board with capacity to act on flagged hits (otherwise the queue grows without resolution).

**Why it's interesting.** This is a publishable methodological contribution in its own right: *evidence-driven maintenance pipelines for canonical clinical artefacts*. Few canonical-resource publishers do this — most rely on manual scanning or external triggers. Documenting the pipeline as part of the DFG proposal (see VISION.md §6) strengthens the "scientific binding" narrative concretely.

---

## Artifact signing (CRMI pattern, FHIR-version-neutral)

**Spec:** [CRMI v2.0.0-ballot — Artifact Signing](https://build.fhir.org/ig/HL7/crmi-ig/en/artifact-signing.html). References [FHIR R6 Digital Signatures](https://build.fhir.org/signatures.html) but the actual mechanics sit on top of standard IETF RFCs (RFC 7515 JWS, RFC 8785 JCS, RFC 7517 JWK), making it FHIR-version-portable.

**Idea.** Sign every PRO Library release manifest (asset-collection `Library`) and every published canonical artefact with a JWS detached signature, distribute the public keys via `/.well-known/jwks.json`, and reference the signature from each resource via the `Link: rel="provenance"` and `X-Provenance` HTTP headers. Consumers verify origin without trusting transport — even a compromised intermediate cache cannot forge content under our key.

**Why we'll need this by 1.0.0.** Three reasons compound:

1. **Normativity claim is meaningless without origin proof.** A consumer pinning `Library/release-x.y.z` needs cryptographic certainty it came from the curating authority — otherwise "normative" reduces to "trust the URL", which is exactly the failure mode this work tries to fix.
2. **Licence gating requires it.** When the mTLS distribution layer proves *who consumes*, signatures must prove *who produced* — symmetric trust. Without producer signatures, an attacker who steals one site's mTLS cert could impersonate the source on a hijacked endpoint.
3. **Audit evidence for licence compliance.** Instrument owners (EORTC, BDI publisher, etc.) will eventually audit how their content is distributed. Signed releases plus mTLS delivery logs together produce verifiable chain-of-custody — much stronger than transport-layer logging alone.

**FHIR R4 vs R6 portability.** The CRMI page references R6, but the pattern works on R4:

| Component | Source | R4-compatible? |
|---|---|---|
| JWS detached + JCS canonicalisation | RFC 7515 + RFC 8785 | yes (IETF, FHIR-version-neutral) |
| JWKS public key distribution | RFC 7517, `/.well-known/jwks.json` | yes (HTTP convention) |
| `Provenance.signature` + `target[].reference` with `\|version` | FHIR Provenance (exists in R4, R5, R6) | yes |
| `Link` / `X-Provenance` HTTP headers | HTTP convention | yes |
| Bundle.entry wrapping of signed Provenance | FHIR Bundle | yes (structure unchanged R4↔R6) |
| `Provenance.signature.sigFormat` / `targetFormat` | R4+ | yes (just need to populate explicitly on R4) |

→ No R6 dependency — we document our JCS conventions explicitly and we're done.

**What would unblock it.**
- 1.0.0 release of the PRO Library (signing pre-1.0 is theatre — the artefacts are explicitly provisional).
- A signing key for the steward authority (whoever it ends up being — see VISION.md §1a). For BIH-CEI provisional stewardship, an institutional X.509 cert from the Charité PKI is the natural starting point.
- A verifier in the form-manager runtime that consumers can pull and run locally (probably co-located with the validator container, since both need the same JWKS access).
- Documentation of the JCS conventions used (since R4 doesn't standardise the canonical form).

**Implementation sketch (when the time comes).**
- Signing job in `pro-library` CI on tag → produces `release-X.Y.Z.jws` files alongside the FHIR Package tarball.
- `pro-library-validator` container learns to verify on `POST /Verify` (separate from `/Validate` which checks profile conformance).
- Form Manager runtime adds `Link: rel="provenance"` and `X-Provenance` headers to every `$package` response.
- Per-consumer manifest signatures may differ — site Manifest is signed by the site, anchored to the (signed) canonical release Manifest.

**Why "in the end" and not earlier.** Cryptographic infrastructure adds operational overhead (key management, rotation, revocation, JWKS hosting, expired-cert recovery) that's only justified once the content is stable enough to make the trust claim meaningful. Pre-1.0 we don't make that claim, so signing would be ceremony without substance.

**Open questions.**
- Single steward key vs. multi-signer (board members co-sign)?
- Revocation strategy — JWKS rotation only, or full PKI revocation (CRLs / OCSP)?
- Signing of *upstream* derivedFrom material — do we sign that we faithfully derived from MII PRO X.Y.Z, or only that we published our derivation?
- Per-language signing — every translation gets its own signature, or one signature spans the multilingual artefact?
