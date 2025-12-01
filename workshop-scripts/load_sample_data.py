#!/usr/bin/env python3
"""
Load sample PROMIS questionnaires and responses for workshop demo
"""

import os
import requests
import time

SITE_A_URL = os.getenv("SITE_A_URL", "http://hapi-site-a:8080/fhir")
SITE_B_URL = os.getenv("SITE_B_URL", "http://hapi-site-b:8080/fhir")


def load_sample_questionnaire():
    """
    Create a sample PROMIS Pain Interference questionnaire on Site A

    Note: In production, this comes from the MII PRO package
    For workshop, we'll create a simple example
    """

    questionnaire = {
        "resourceType": "Questionnaire",
        "id": "promis-pain-interference-6a-demo",
        "url": "http://loinc.org/Questionnaire/62629-8",
        "version": "1.0",
        "name": "PROMISPainInterference6a",
        "title": "PROMIS Pain Interference 6a (Demo)",
        "status": "active",
        "date": "2024-11-27",
        "code": [{
            "system": "http://loinc.org",
            "code": "62629-8",
            "display": "PROMIS pain interference - version 1.0"
        }],
        "item": [
            {
                "linkId": "61758-9",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "61758-9"
                }],
                "text": "In the past 7 days, how much did pain interfere with your day to day activities?",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            },
            {
                "linkId": "61769-6",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "61769-6"
                }],
                "text": "In the past 7 days, how much did pain interfere with work around the home?",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            }
        ]
    }

    print("\n📝 Creating sample PROMIS questionnaire on Site A...")
    try:
        response = requests.put(
            f"{SITE_A_URL}/Questionnaire/promis-pain-interference-6a-demo",
            json=questionnaire,
            headers={"Content-Type": "application/fhir+json"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print("  ✓ Questionnaire created")
            return True
        else:
            print(f"  ⚠️ Questionnaire creation returned: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Error creating questionnaire: {e}")
        return False


def load_sample_questionnaire_phq9():
    """
    Create PHQ-9 (depression screening) questionnaire on Site A
    """

    questionnaire = {
        "resourceType": "Questionnaire",
        "id": "phq-9-demo",
        "url": "http://loinc.org/Questionnaire/44249-1",
        "version": "1.0",
        "name": "PHQ9",
        "title": "Patient Health Questionnaire-9 (PHQ-9) (Demo)",
        "status": "active",
        "date": "2024-11-27",
        "code": [{
            "system": "http://loinc.org",
            "code": "44249-1",
            "display": "PHQ-9 quick depression assessment panel"
        }],
        "item": [
            {
                "linkId": "44250-9",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "44250-9"
                }],
                "text": "Little interest or pleasure in doing things",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            },
            {
                "linkId": "44255-8",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "44255-8"
                }],
                "text": "Feeling down, depressed, or hopeless",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            },
            {
                "linkId": "44259-0",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "44259-0"
                }],
                "text": "Trouble falling or staying asleep, or sleeping too much",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            },
            {
                "linkId": "44254-1",
                "code": [{
                    "system": "http://loinc.org",
                    "code": "44254-1"
                }],
                "text": "Feeling tired or having little energy",
                "type": "choice",
                "required": True,
                "answerValueSet": "http://loinc.org/vs/LL358-3"
            }
        ]
    }

    print("\n📝 Creating PHQ-9 questionnaire on Site A...")
    try:
        response = requests.put(
            f"{SITE_A_URL}/Questionnaire/phq-9-demo",
            json=questionnaire,
            headers={"Content-Type": "application/fhir+json"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print("  ✓ PHQ-9 Questionnaire created")
            return True
        else:
            print(f"  ⚠️ PHQ-9 creation returned: {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  ✗ Error creating PHQ-9: {e}")
        return False


def load_sample_response():
    """
    Create a sample QuestionnaireResponse on Site A (PROMIS)
    """

    response_data = {
        "resourceType": "QuestionnaireResponse",
        "id": "demo-response-1",
        "questionnaire": "http://loinc.org/Questionnaire/62629-8",
        "status": "completed",
        "authored": "2024-11-27T10:00:00Z",
        "item": [
            {
                "linkId": "61758-9",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA13914-9",
                        "display": "Quite a bit"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 4
                    }]
                }]
            },
            {
                "linkId": "61769-6",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA13902-4",
                        "display": "Somewhat"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 3
                    }]
                }]
            }
        ]
    }

    print("\n📋 Creating sample PROMIS QuestionnaireResponse on Site A...")
    try:
        response = requests.put(
            f"{SITE_A_URL}/QuestionnaireResponse/demo-response-1",
            json=response_data,
            headers={"Content-Type": "application/fhir+json"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print("  ✓ PROMIS QuestionnaireResponse created")
            return True
        else:
            print(f"  ⚠️ Response creation returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error creating response: {e}")
        return False


def load_sample_response_phq9():
    """
    Create a sample PHQ-9 QuestionnaireResponse on Site A
    """

    response_data = {
        "resourceType": "QuestionnaireResponse",
        "id": "demo-response-phq9-1",
        "questionnaire": "http://loinc.org/Questionnaire/44249-1",
        "status": "completed",
        "authored": "2024-11-27T10:00:00Z",
        "item": [
            {
                "linkId": "44250-9",
                "text": "Little interest or pleasure in doing things",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA6570-1",
                        "display": "More than half the days"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 2
                    }]
                }]
            },
            {
                "linkId": "44255-8",
                "text": "Feeling down, depressed, or hopeless",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA6569-3",
                        "display": "Several days"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 1
                    }]
                }]
            },
            {
                "linkId": "44259-0",
                "text": "Trouble falling or staying asleep, or sleeping too much",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA6570-1",
                        "display": "More than half the days"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 2
                    }]
                }]
            },
            {
                "linkId": "44254-1",
                "text": "Feeling tired or having little energy",
                "answer": [{
                    "valueCoding": {
                        "system": "http://loinc.org",
                        "code": "LA6571-9",
                        "display": "Nearly every day"
                    },
                    "extension": [{
                        "url": "http://hl7.org/fhir/StructureDefinition/ordinalValue",
                        "valueDecimal": 3
                    }]
                }]
            }
        ]
    }

    print("\n📋 Creating sample PHQ-9 QuestionnaireResponse on Site A...")
    try:
        response = requests.put(
            f"{SITE_A_URL}/QuestionnaireResponse/demo-response-phq9-1",
            json=response_data,
            headers={"Content-Type": "application/fhir+json"},
            timeout=10
        )

        if response.status_code in [200, 201]:
            print("  ✓ PHQ-9 QuestionnaireResponse created")
            return True
        else:
            print(f"  ⚠️ PHQ-9 response creation returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ✗ Error creating PHQ-9 response: {e}")
        return False


def main():
    """Load all sample data"""
    print("=" * 50)
    print("Loading Sample Data for Workshop")
    print("=" * 50)

    # Wait a bit to ensure HAPI is fully initialized
    print("\nWaiting 10s for HAPI to fully initialize...")
    time.sleep(10)

    success = True

    # Load PROMIS questionnaire
    if not load_sample_questionnaire():
        success = False

    # Load PHQ-9 questionnaire
    if not load_sample_questionnaire_phq9():
        success = False

    # Load PROMIS response
    if not load_sample_response():
        success = False

    # Load PHQ-9 response
    if not load_sample_response_phq9():
        success = False

    print("\n" + "=" * 50)
    if success:
        print("✓ Sample data loaded successfully!")
        print("  - PROMIS Pain Interference questionnaire & response")
        print("  - PHQ-9 depression screening questionnaire & response")
    else:
        print("⚠️ Some sample data failed to load")
        print("  This is normal if HAPI is still initializing")
        print("  Data will be available from packages")
    print("=" * 50)

    return 0  # Don't fail if sample data doesn't load


if __name__ == "__main__":
    import sys
    sys.exit(main())
