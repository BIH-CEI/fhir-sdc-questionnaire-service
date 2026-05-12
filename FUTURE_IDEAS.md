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
