// What a client sees behind the mTLS proxy: HAPI and the sidecar answer under
// one FHIR base. Operations served by the sidecar are marked in their docs.

Instance: sdc-form-manager
InstanceOf: CapabilityStatement
Usage: #definition
Title: "SDC Form Manager"
* url = "https://bih-cei.github.io/fhir-sdc-questionnaire-service/CapabilityStatement/sdc-form-manager"
* name = "SDCFormManager"
* title = "SDC Form Manager"
* status = #draft
* experimental = false
* date = "2026-10-19"
* publisher = "Berlin Institute of Health at Charité (BIH-CEI)"
* description = "Capabilities of the BIH-CEI SDC Form Manager as seen by clients through the mTLS proxy: HAPI FHIR 8.12 (content, terminology, Clinical Reasoning) plus the sidecar operations under the same FHIR base."
* kind = #instance
* instantiates = "http://hl7.org/fhir/uv/sdc/CapabilityStatement/sdc-form-manager"
* software.name = "BIH-CEI FHIR SDC Form Manager"
* software.version = "0.2.0"
* implementation.description = "HAPI FHIR 8.12 (hapiproject/hapi v8.12.0-2, cqf-fhir-cr 4.13.0) with FastAPI sidecar behind an nginx mTLS proxy"
* fhirVersion = #4.0.1
* format[0] = #json
* format[+] = #xml

* rest[0].mode = #server
* rest[=].documentation = "One FHIR base (`[base]/fhir/`). `$package`, `$localize`, `$languages` and `$compute-and-extract` on Questionnaire are answered by the sidecar; everything else by HAPI. Errors are OperationOutcome resources."
* rest[=].security.description = "Mutual TLS: a client certificate issued by a trusted CA is required (401 otherwise), and its SHA-1 fingerprint must be on the site allowlist (403 otherwise). See the Access page."

* rest[=].resource[0].type = #Questionnaire
* rest[=].resource[=].versioning = #versioned
* rest[=].resource[=].interaction[0].code = #read
* rest[=].resource[=].interaction[+].code = #vread
* rest[=].resource[=].interaction[+].code = #search-type
* rest[=].resource[=].searchParam[0].name = "url"
* rest[=].resource[=].searchParam[=].type = #uri
* rest[=].resource[=].searchParam[+].name = "version"
* rest[=].resource[=].searchParam[=].type = #token
* rest[=].resource[=].searchParam[+].name = "status"
* rest[=].resource[=].searchParam[=].type = #token
* rest[=].resource[=].operation[0].name = "package"
* rest[=].resource[=].operation[=].definition = "http://hl7.org/fhir/uv/crmi/OperationDefinition/crmi-package"
* rest[=].resource[=].operation[=].documentation = "Sidecar. CRMI package: outcome manifest (Library asset-collection) first, then the Questionnaire and its dependencies. See Operations."
* rest[=].resource[=].operation[+].name = "localize"
* rest[=].resource[=].operation[=].definition = Canonical(QuestionnaireLocalize)
* rest[=].resource[=].operation[+].name = "languages"
* rest[=].resource[=].operation[=].definition = Canonical(QuestionnaireLanguages)
* rest[=].resource[=].operation[+].name = "compute-and-extract"
* rest[=].resource[=].operation[=].definition = Canonical(QuestionnaireComputeAndExtract)
* rest[=].resource[=].operation[+].name = "populate"
* rest[=].resource[=].operation[=].definition = "http://hl7.org/fhir/uv/sdc/OperationDefinition/Questionnaire-populate"
* rest[=].resource[=].operation[=].documentation = "HAPI Clinical Reasoning."

* rest[=].resource[+].type = #QuestionnaireResponse
* rest[=].resource[=].interaction[0].code = #create
* rest[=].resource[=].interaction[+].code = #read
* rest[=].resource[=].interaction[+].code = #search-type
* rest[=].resource[=].operation[0].name = "extract"
* rest[=].resource[=].operation[=].definition = "http://hl7.org/fhir/uv/sdc/OperationDefinition/QuestionnaireResponse-extract"
* rest[=].resource[=].operation[=].documentation = "HAPI Clinical Reasoning (does not evaluate calculatedExpression; use $compute-and-extract for scores)."

* rest[=].resource[+].type = #ValueSet
* rest[=].resource[=].interaction[0].code = #read
* rest[=].resource[=].interaction[+].code = #search-type
* rest[=].resource[=].operation[0].name = "expand"
* rest[=].resource[=].operation[=].definition = "http://hl7.org/fhir/OperationDefinition/ValueSet-expand"
* rest[=].resource[=].operation[=].documentation = "Runtime expansion; the packages ship ValueSets without expansion."

* rest[=].resource[+].type = #CodeSystem
* rest[=].resource[=].interaction[0].code = #read
* rest[=].resource[=].interaction[+].code = #search-type
* rest[=].resource[=].operation[0].name = "lookup"
* rest[=].resource[=].operation[=].definition = "http://hl7.org/fhir/OperationDefinition/CodeSystem-lookup"

* rest[=].resource[+].type = #Library
* rest[=].resource[=].interaction[0].code = #read
* rest[=].resource[=].interaction[+].code = #search-type
* rest[=].resource[=].documentation = "Scoring CQL Libraries and CRMI release manifests (asset-collection)."

* rest[=].resource[+].type = #ObservationDefinition
* rest[=].resource[=].interaction[0].code = #read
* rest[=].resource[=].interaction[+].code = #search-type
