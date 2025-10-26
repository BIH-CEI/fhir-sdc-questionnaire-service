"""Sample FHIR resources for testing."""

# PHQ-2 Depression Screening (2 questions)
PHQ2_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "id": "phq-2",
    "url": "http://example.org/Questionnaire/phq-2",
    "version": "1.0.0",
    "status": "active",
    "title": "PHQ-2 Depression Screening",
    "description": "Patient Health Questionnaire-2 for depression screening",
    "item": [
        {
            "linkId": "1",
            "text": "Little interest or pleasure in doing things?",
            "type": "choice",
            "required": True,
            "answerValueSet": "http://example.org/ValueSet/phq2-frequency"
        },
        {
            "linkId": "2",
            "text": "Feeling down, depressed, or hopeless?",
            "type": "choice",
            "required": True,
            "answerValueSet": "http://example.org/ValueSet/phq2-frequency"
        }
    ]
}

PHQ2_VALUESET = {
    "resourceType": "ValueSet",
    "id": "phq2-frequency",
    "url": "http://example.org/ValueSet/phq2-frequency",
    "version": "1.0.0",
    "status": "active",
    "name": "PHQ2Frequency",
    "title": "PHQ-2 Frequency Answers",
    "description": "Frequency answers for PHQ-2 questions",
    "compose": {
        "include": [
            {
                "system": "http://example.org/CodeSystem/phq-frequency",
                "concept": [
                    {"code": "not-at-all", "display": "Not at all"},
                    {"code": "several-days", "display": "Several days"},
                    {"code": "more-than-half", "display": "More than half the days"},
                    {"code": "nearly-every-day", "display": "Nearly every day"}
                ]
            }
        ]
    }
}

PHQ2_CODESYSTEM = {
    "resourceType": "CodeSystem",
    "id": "phq-frequency",
    "url": "http://example.org/CodeSystem/phq-frequency",
    "version": "1.0.0",
    "status": "active",
    "name": "PHQFrequency",
    "title": "PHQ Frequency Code System",
    "content": "complete",
    "concept": [
        {"code": "not-at-all", "display": "Not at all"},
        {"code": "several-days", "display": "Several days"},
        {"code": "more-than-half", "display": "More than half the days"},
        {"code": "nearly-every-day", "display": "Nearly every day"}
    ]
}

# Diabetes Screening Questionnaire
DIABETES_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "id": "diabetes-screening",
    "url": "http://example.org/Questionnaire/diabetes-screening",
    "version": "2.0.0",
    "status": "active",
    "title": "Diabetes Risk Assessment",
    "description": "Questionnaire for assessing diabetes risk factors",
    "item": [
        {
            "linkId": "1",
            "text": "What is your age?",
            "type": "integer",
            "required": True
        },
        {
            "linkId": "2",
            "text": "What is your fasting glucose level?",
            "type": "choice",
            "required": True,
            "answerValueSet": "http://example.org/ValueSet/glucose-levels"
        },
        {
            "linkId": "3",
            "text": "Do you have a family history of diabetes?",
            "type": "boolean",
            "required": True
        },
        {
            "linkId": "4",
            "text": "Additional risk factors",
            "type": "group",
            "item": [
                {
                    "linkId": "4.1",
                    "text": "Are you physically active?",
                    "type": "boolean"
                },
                {
                    "linkId": "4.2",
                    "text": "Body Mass Index (BMI)",
                    "type": "decimal"
                }
            ]
        }
    ]
}

GLUCOSE_VALUESET = {
    "resourceType": "ValueSet",
    "id": "glucose-levels",
    "url": "http://example.org/ValueSet/glucose-levels",
    "version": "1.0.0",
    "status": "active",
    "name": "GlucoseLevels",
    "title": "Glucose Level Ranges",
    "compose": {
        "include": [
            {
                "system": "http://loinc.org",
                "concept": [
                    {"code": "15074-8", "display": "Glucose [Moles/volume] in Blood"},
                    {"code": "2339-0", "display": "Glucose [Mass/volume] in Blood"}
                ]
            }
        ]
    }
}

# Questionnaire with missing dependencies (for error testing)
QUESTIONNAIRE_WITH_MISSING_VALUESET = {
    "resourceType": "Questionnaire",
    "status": "draft",
    "title": "Test Questionnaire with Missing Dependencies",
    "item": [
        {
            "linkId": "1",
            "text": "Question with missing ValueSet",
            "type": "choice",
            "answerValueSet": "http://example.org/ValueSet/DOES_NOT_EXIST"
        }
    ]
}

# Questionnaire with nested items (complex structure)
COMPLEX_NESTED_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "status": "active",
    "title": "Complex Nested Questionnaire",
    "item": [
        {
            "linkId": "1",
            "text": "Patient Demographics",
            "type": "group",
            "item": [
                {
                    "linkId": "1.1",
                    "text": "Name",
                    "type": "string"
                },
                {
                    "linkId": "1.2",
                    "text": "Gender",
                    "type": "choice",
                    "answerValueSet": "http://example.org/ValueSet/phq2-frequency"
                },
                {
                    "linkId": "1.3",
                    "text": "Contact Information",
                    "type": "group",
                    "item": [
                        {
                            "linkId": "1.3.1",
                            "text": "Phone",
                            "type": "string"
                        },
                        {
                            "linkId": "1.3.2",
                            "text": "Preferred Contact Method",
                            "type": "choice",
                            "answerValueSet": "http://example.org/ValueSet/phq2-frequency"
                        }
                    ]
                }
            ]
        }
    ]
}

# Simple questionnaire with no dependencies
SIMPLE_TEXT_QUESTIONNAIRE = {
    "resourceType": "Questionnaire",
    "status": "active",
    "title": "Simple Text-Only Questionnaire",
    "item": [
        {
            "linkId": "1",
            "text": "What is your name?",
            "type": "string"
        },
        {
            "linkId": "2",
            "text": "What is your date of birth?",
            "type": "date"
        },
        {
            "linkId": "3",
            "text": "Additional comments",
            "type": "text"
        }
    ]
}

# Questionnaire with Library reference (for CQL/FHIRPath)
QUESTIONNAIRE_WITH_LIBRARY = {
    "resourceType": "Questionnaire",
    "status": "active",
    "title": "BMI Calculator Questionnaire",
    "extension": [
        {
            "url": "http://hl7.org/fhir/StructureDefinition/cqf-library",
            "valueCanonical": "http://example.org/Library/bmi-calculator|1.0"
        }
    ],
    "item": [
        {
            "linkId": "1",
            "text": "Height (cm)",
            "type": "decimal"
        },
        {
            "linkId": "2",
            "text": "Weight (kg)",
            "type": "decimal"
        },
        {
            "linkId": "3",
            "text": "BMI (calculated)",
            "type": "decimal",
            "readOnly": True
        }
    ]
}

SAMPLE_LIBRARY = {
    "resourceType": "Library",
    "id": "bmi-calculator",
    "url": "http://example.org/Library/bmi-calculator",
    "version": "1.0",
    "status": "active",
    "type": {
        "coding": [
            {
                "system": "http://terminology.hl7.org/CodeSystem/library-type",
                "code": "logic-library"
            }
        ]
    },
    "content": [
        {
            "contentType": "text/cql",
            "data": "bGlicmFyeSBCTUlDYWxjdWxhdG9yIHZlcnNpb24gJzEuMCc="
        }
    ]
}
