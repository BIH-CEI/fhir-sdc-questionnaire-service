// Operations the sidecar adds. $package is CRMI's crmi-package (not redefined
// here); see the Operations page and the example package Bundle.

Instance: QuestionnaireLocalize
InstanceOf: OperationDefinition
Usage: #definition
Title: "Questionnaire $localize"
* url = "https://bih-cei.github.io/fhir-sdc-questionnaire-service/OperationDefinition/QuestionnaireLocalize"
* name = "QuestionnaireLocalize"
* title = "Questionnaire $localize"
* status = #draft
* kind = #operation
* code = #localize
* resource = #Questionnaire
* system = false
* type = true
* instance = true
* affectsState = false
* description = "Returns the Questionnaire rendered in one language: item texts, answer displays and `answerOption.valueCoding.display` are replaced by their `translation` extension for the requested language. Type level: either `url` (+ optional `version`) as query parameters, or POST the Questionnaire itself as the request body (not wrapped in Parameters)."
* parameter[0].name = #url
* parameter[=].use = #in
* parameter[=].min = 0
* parameter[=].max = "1"
* parameter[=].type = #uri
* parameter[=].documentation = "Canonical URL of the Questionnaire (type level, GET)."
* parameter[+].name = #version
* parameter[=].use = #in
* parameter[=].min = 0
* parameter[=].max = "1"
* parameter[=].type = #string
* parameter[=].documentation = "Business version; without it the highest active version is used."
* parameter[+].name = #language
* parameter[=].use = #in
* parameter[=].min = 1
* parameter[=].max = "1"
* parameter[=].type = #code
* parameter[=].documentation = "Target language (BCP-47), e.g. `de`."
* parameter[+].name = #return
* parameter[=].use = #out
* parameter[=].min = 1
* parameter[=].max = "1"
* parameter[=].type = #Questionnaire
* parameter[=].documentation = "The localized Questionnaire."

Instance: QuestionnaireLanguages
InstanceOf: OperationDefinition
Usage: #definition
Title: "Questionnaire $languages"
* url = "https://bih-cei.github.io/fhir-sdc-questionnaire-service/OperationDefinition/QuestionnaireLanguages"
* name = "QuestionnaireLanguages"
* title = "Questionnaire $languages"
* status = #draft
* kind = #operation
* code = #languages
* resource = #Questionnaire
* system = false
* type = false
* instance = true
* affectsState = false
* description = "Lists the languages a Questionnaire can be localized to (its own language plus every language found in `translation` extensions), so clients can offer a choice before calling `$localize`."
* parameter[0].name = #language
* parameter[=].use = #out
* parameter[=].min = 0
* parameter[=].max = "*"
* parameter[=].type = #code
* parameter[=].documentation = "One entry per available language."

Instance: QuestionnaireComputeAndExtract
InstanceOf: OperationDefinition
Usage: #definition
Title: "Questionnaire $compute-and-extract"
* url = "https://bih-cei.github.io/fhir-sdc-questionnaire-service/OperationDefinition/QuestionnaireComputeAndExtract"
* name = "QuestionnaireComputeAndExtract"
* title = "Questionnaire $compute-and-extract"
* status = #draft
* kind = #operation
* code = #compute-and-extract
* resource = #Questionnaire
* system = false
* type = false
* instance = true
* affectsState = true
* description = "Evaluates the Questionnaire's scoring CQL (`cqf-library`) for a subject and turns the results into Observations: `item.code` becomes `Observation.code`, the item's CQL `calculatedExpression` names the define, `ObservationDefinition.qualifiedInterval` supplies the interpretation. Bridges a gap in HAPI Clinical Reasoning, whose `$extract` does not evaluate `calculatedExpression`. The subject's QuestionnaireResponse must already be on the server. Query parameter `persist=false` returns the transaction Bundle instead of storing it."
* parameter[0].name = #subject
* parameter[=].use = #in
* parameter[=].min = 1
* parameter[=].max = "1"
* parameter[=].type = #Reference
* parameter[=].targetProfile = "http://hl7.org/fhir/StructureDefinition/Patient"
* parameter[=].documentation = "The patient whose most recent QuestionnaireResponse is scored."
* parameter[+].name = #persist
* parameter[=].use = #in
* parameter[=].min = 0
* parameter[=].max = "1"
* parameter[=].type = #boolean
* parameter[=].documentation = "Query parameter, default true: store the Observations. false: return the transaction Bundle for caller-side persistence."
* parameter[+].name = #return
* parameter[=].use = #out
* parameter[=].min = 1
* parameter[=].max = "1"
* parameter[=].type = #Bundle
* parameter[=].documentation = "The created Observations (collection Bundle), or the unsent transaction Bundle when persist=false."
