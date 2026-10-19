The **BIH-CEI FHIR SDC Form Manager** is a central source for FHIR-encoded patient-reported outcome measures (PROMs). Sites fetch Questionnaires together with their terminology and scoring logic over standard FHIR, authenticated by client certificates.

This guide is the contract for those sites and for the people who run the service: which operations exist, what content is served in which version, how access works, and how the service is deployed and maintained.

### What it is

| Part | Role |
|------|------|
| **Form Manager** (HAPI FHIR 8.12) | Stores and serves all content; terminology (`ValueSet/$expand`); Clinical Reasoning (`$populate`, `$extract`, CQL `Library/$evaluate`) |
| **Sidecar** (FastAPI) | Operations HAPI lacks or gets wrong: CRMI `$package`, `$localize`, `$languages`, `$compute-and-extract` |
| **mTLS proxy** (nginx) | The only entry point: client-certificate check, site allowlist, one FHIR base |

For clients it is **one FHIR server** at `https://<host>/fhir/`. The [CapabilityStatement](CapabilityStatement-sdc-form-manager.html) lists what it supports.

### Content

MII PRO (Kerndatensatz-Modul PRO), the BIH-CEI PRO Library (with CQL scoring) and PCOR-MII are baked into the server image, with SDC as the forms standard. See [Content and Versions](content.html).

### Where to go next

- **Using the service as a site:** [Operations](operations.html), [Access (mTLS)](access.html), [Errors](errors.html)
- **Running the service:** [Deployment](deployment.html), [Maintenance](maintenance.html)
- **Source code:** [github.com/BIH-CEI/fhir-sdc-questionnaire-service](https://github.com/BIH-CEI/fhir-sdc-questionnaire-service)

### Status

Pilot. The current image serves the MII PRO **2027 ballot** content for testing before the final release. See [Maintenance](maintenance.html) for what is not production-ready yet.
