All operations live under one FHIR base, `https://<host>/fhir/`. The proxy routes the Questionnaire operations marked *sidecar* to the FastAPI sidecar and everything else to HAPI.

| Operation | Served by | Definition |
|-----------|-----------|------------|
| `Questionnaire/[id]/$package`, `Questionnaire/$package?url=…[&version=…]` | sidecar | [CRMI `crmi-package`](http://hl7.org/fhir/uv/crmi/OperationDefinition/crmi-package) |
| `Questionnaire/[id]/$localize?language=…`, `Questionnaire/$localize` | sidecar | [$localize](OperationDefinition-QuestionnaireLocalize.html) |
| `Questionnaire/[id]/$languages` | sidecar | [$languages](OperationDefinition-QuestionnaireLanguages.html) |
| `Questionnaire/[id]/$compute-and-extract` | sidecar | [$compute-and-extract](OperationDefinition-QuestionnaireComputeAndExtract.html) |
| `Questionnaire/$populate` | HAPI (Clinical Reasoning) | [SDC](http://hl7.org/fhir/uv/sdc/OperationDefinition/Questionnaire-populate) |
| `QuestionnaireResponse/$extract` | HAPI (Clinical Reasoning) | [SDC](http://hl7.org/fhir/uv/sdc/OperationDefinition/QuestionnaireResponse-extract) |
| `ValueSet/$expand`, `CodeSystem/$lookup` | HAPI | FHIR core |
| read, vread, search on Questionnaire, ValueSet, CodeSystem, Library, ObservationDefinition | HAPI | FHIR core |

### $package

SDC defines no `$package`; the operation comes from CRMI. CRMI requires that *"the first resource returned in the resulting package will be an outcome manifest"*. The sidecar returns a `collection` Bundle:

1. **Outcome manifest**: a `Library` of type `asset-collection` (profile `crmi-manifestlibrary`). It lists
   - the packaged Questionnaire as `composed-of`,
   - every referenced dependency as `depends-on`, with the exact `url|version` that was packaged; unresolved ones as referenced,
   - packaging messages (e.g. a ValueSet that is not on the server) as a contained `OperationOutcome`, referenced by `cqf-messages`. **Clients SHALL check these messages.**
2. The **Questionnaire**.
3. Its **dependencies**: answer ValueSets and their CodeSystems, `cqf-library` Libraries (transitively), `targetStructureMap`s.

Parameter `include-dependencies=false` returns only manifest and Questionnaire. An unversioned reference resolves to the Questionnaire's own package version if present, otherwise to the highest active version. Limits: 100 entries, 20 MB.

See the [example package](Bundle-example-package.html).

HAPI's own `$package` is not used: in cqf-fhir-cr up to 4.13.0 it crashes on almost all MII PRO and PCOR-MII Questionnaires because it never creates the outcome manifest for Questionnaire roots.

### Terminology at runtime

The content packages ship ValueSets **without expansions**. Expand `answerValueSet`s at runtime with `ValueSet/$expand?url=…`. For about a minute after a fresh server start, expansions can be empty while HAPI pre-expands ValueSets in the background.

### Scores

`$compute-and-extract` evaluates the scoring CQL of a Questionnaire for a patient and creates Observations. HAPI's `$extract` does not evaluate `sdc-calculatedExpression`, so scores need this operation. The subject's QuestionnaireResponse must be on the server first.
