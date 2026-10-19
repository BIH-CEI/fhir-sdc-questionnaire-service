// Shape of a $package result (CRMI): outcome manifest first.

Instance: example-package-manifest
InstanceOf: Library
Usage: #inline
* meta.profile = "http://hl7.org/fhir/uv/crmi/StructureDefinition/crmi-manifestlibrary"
* status = #active
* type = http://terminology.hl7.org/CodeSystem/library-type#asset-collection
* title = "Package of Example Questionnaire"
* date = "2026-10-19"
* extension[0].url = "http://hl7.org/fhir/StructureDefinition/cqf-messages"
* extension[=].valueReference.reference = "#messages"
* contained[0] = example-package-messages
* relatedArtifact[0].type = #composed-of
* relatedArtifact[=].display = "Example Questionnaire"
* relatedArtifact[=].resource = "https://example.org/fhir/Questionnaire/example|1.0.0"
* relatedArtifact[+].type = #depends-on
* relatedArtifact[=].display = "Example answers"
* relatedArtifact[=].resource = "https://example.org/fhir/ValueSet/example-answers|1.0.0"
* relatedArtifact[+].type = #depends-on
* relatedArtifact[=].resource = "https://example.org/fhir/ValueSet/not-on-server"

Instance: example-package-messages
InstanceOf: OperationOutcome
Usage: #inline
* id = "messages"
* issue[0].severity = #warning
* issue[=].code = #not-found
* issue[=].diagnostics = "Referenced ValueSet not found: https://example.org/fhir/ValueSet/not-on-server"

Instance: example-package-questionnaire
InstanceOf: Questionnaire
Usage: #inline
* url = "https://example.org/fhir/Questionnaire/example"
* version = "1.0.0"
* status = #active
* title = "Example Questionnaire"
* item[0].linkId = "q1"
* item[=].text = "How are you?"
* item[=].type = #choice
* item[=].answerValueSet = "https://example.org/fhir/ValueSet/example-answers"
* item[+].linkId = "q2"
* item[=].text = "Anything else?"
* item[=].type = #choice
* item[=].answerValueSet = "https://example.org/fhir/ValueSet/not-on-server"

Instance: example-package-valueset
InstanceOf: ValueSet
Usage: #inline
* url = "https://example.org/fhir/ValueSet/example-answers"
* version = "1.0.0"
* status = #active
* name = "ExampleAnswers"
* title = "Example answers"
* description = "Answer options of the example Questionnaire."
* experimental = true
* compose.include[0].system = "https://example.org/fhir/CodeSystem/example"
* compose.include[=].concept[0].code = #good
* compose.include[=].concept[+].code = #bad

Instance: example-package
InstanceOf: Bundle
Usage: #example
Title: "Example $package result"
Description: "A CRMI package as returned by the sidecar: the outcome manifest (entry 1) lists the Questionnaire (composed-of) and each referenced dependency (depends-on, with the packaged url|version); the missing ValueSet is reported in the manifest's contained OperationOutcome."
* type = #collection
* timestamp = "2026-10-19T08:00:00Z"
* entry[0].fullUrl = "urn:uuid:3f1e1a1c-0000-4000-8000-000000000001"
* entry[=].resource = example-package-manifest
* entry[+].fullUrl = "urn:uuid:3f1e1a1c-0000-4000-8000-000000000002"
* entry[=].resource = example-package-questionnaire
* entry[+].fullUrl = "urn:uuid:3f1e1a1c-0000-4000-8000-000000000003"
* entry[=].resource = example-package-valueset

Instance: example-error
InstanceOf: OperationOutcome
Usage: #example
Title: "Example error"
Description: "Error body of the sidecar (here: 404 for an unknown Questionnaire); every 4xx/5xx is an OperationOutcome."
* issue[0].severity = #error
* issue[=].code = #not-found
* issue[=].diagnostics = "Questionnaire with id 'does-not-exist' not found"
