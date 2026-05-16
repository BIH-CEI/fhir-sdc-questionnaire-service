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
