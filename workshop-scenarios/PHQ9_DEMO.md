# PHQ-9 Depression Screening in Workshop

## Overview

PHQ-9 (Patient Health Questionnaire-9) is now included in the workshop alongside PROMIS Pain Interference. This demonstrates a simpler scoring model (sum score 0-27) compared to PROMIS's complex IRT scoring.

## What's Available

### Questionnaire
- **LOINC Panel:** 44249-1
- **Name:** PHQ-9 quick depression assessment panel
- **Items:** 9 questions about depression symptoms over past 2 weeks
- **Scoring:** Simple sum (0-3 per item, total 0-27)

### Answer Options (LOINC: LL358-9)
| Code | English | German | Turkish | Score |
|------|---------|--------|---------|-------|
| LA6568-5 | Not at all | Überhaupt nicht | Hiç | 0 |
| LA6569-3 | Several days | An einzelnen Tagen | Birkaç gün | 1 |
| LA6570-1 | More than half the days | An mehr als der Hälfte der Tage | ❌ Missing | 2 |
| LA6571-9 | Nearly every day | Beinahe jeden Tag | ❌ Missing | 3 |

### PHQ-9 Score Interpretation
- **0-4:** Minimal depression
- **5-9:** Mild depression
- **10-14:** Moderate depression
- **15-19:** Moderately severe depression
- **20-27:** Severe depression

## Demo Scenarios with PHQ-9

### Scenario 1: Simple Sum Scoring vs Complex IRT
**Comparison:**
- **PHQ-9:** Simple sum (easy to calculate, any system can do it)
- **PROMIS:** IRT-based T-scores (requires specialized algorithms)

**Shows:**
- Not all PROMs need complex scoring
- Simpler instruments may have better adoption
- Trade-off: Simplicity vs psychometric sophistication

### Scenario 2: Cross-Cultural Stigma
**Challenge:**
- Item: "Feeling down, depressed, or hopeless"
- German: "Sich niedergeschlagen, deprimiert oder hoffnungslos fühlen"
- Turkish: Direct translation exists BUT...

**Cultural Issue:**
- "Depression" (depresif) carries heavy stigma in some cultures
- Patients may under-report due to mental health stigma
- Translation alone insufficient - need cross-cultural adaptation

**Demonstrates:**
- Why literal translation ≠ cross-cultural adaptation
- Need for cultural validation studies
- Governance challenge: When is adaptation required?

### Scenario 3: Clinical Decision Support
**PHQ-9 Score Interpretation:**

```
Sample Response: Total Score = 8

Automatic Interpretation:
├── Score: 8
├── Severity: Mild depression
├── Clinical Action:
│   ├── Watchful waiting
│   ├── Repeat PHQ-9 in 2 weeks
│   └── Consider support/counseling
│
└── Critical Item Check:
    Item 9 (self-harm): "Not at all"
    → No immediate safety concern
```

**If Item 9 > 0:**
```
ALERT: Suicidal ideation detected!
├── Score on Item 9: "Several days" (1)
├── Required Actions:
│   ├── Immediate clinical evaluation
│   ├── Safety assessment
│   └── Flag in EHR
│
└── Governance Question:
    WHO validates this algorithm?
    Clinical society? Technical team? Both?
```

## API Examples

### Get PHQ-9 Questionnaire
```bash
# From terminology proxy (auto-generated from LOINC panel)
curl "http://localhost:3000/loinc/Panel/44249-1?format=Questionnaire" | jq

# From HAPI (loaded sample)
curl "http://localhost:8081/fhir/Questionnaire/phq-9-demo" | jq
```

### Get PHQ-9 Answer Options
```bash
# English with ordinals
curl "http://localhost:3000/loinc/AnswerList/LL358-9?include=ordinals" | jq

# German
curl "http://localhost:3000/loinc/AnswerList/LL358-9?displayLanguage=de" | jq

# Turkish (shows missing translations!)
curl "http://localhost:3000/loinc/AnswerList/LL358-9?displayLanguage=tr" | jq
```

### Get Sample Response
```bash
# Sample PHQ-9 response (Score: 8 - Mild depression)
curl "http://localhost:8081/fhir/QuestionnaireResponse/demo-response-phq9-1" | jq
```

### Calculate Score
```bash
# Manual calculation from response
curl "http://localhost:8081/fhir/QuestionnaireResponse/demo-response-phq9-1" | \
  jq '[.item[].answer[0].extension[0].valueDecimal] | add'

# Result: 8 (2 + 1 + 2 + 3)
```

## Workshop Discussion Points

### 1. Scoring Complexity Spectrum
```
Simple ←──────────────────────────────────→ Complex

PHQ-9              VAS Scale              PROMIS
(Sum 0-27)         (0-100)               (IRT T-scores)
├─ Easy            ├─ Moderate            ├─ Complex
├─ Any system      ├─ Linear calc         ├─ Specialized libs
└─ Less precise    └─ Simple              └─ Psychometric power

Question: Where should MII focus standardization efforts?
- Support all types?
- Prioritize simple scoring?
- Invest in IRT infrastructure?
```

### 2. Clinical Decision Support Integration
```
Scenario: PHQ-9 Score = 15 (Moderately Severe)

Current State:
├── Clinician manually interprets score
├── Looks up guidelines
└── Makes treatment decision

Desired State:
├── Automatic severity classification
├── Guideline-based recommendations
├── EHR decision support integration

Technical Challenge:
├── Where does algorithm live?
│   ├── In FHIR Questionnaire? (Not really supported)
│   ├── In CQL Library? (Complex)
│   ├── In ObservationDefinition? (Metadata only)
│   └─ In EHR system? (Fragmented)
│
└── Who validates clinical algorithms?
    ├── AWMF? (Medical societies)
    ├── Sites? (Local committees)
    └── MII? (Technical coordination)
```

### 3. Suicide Risk Detection
```
PHQ-9 Item 9: "Thoughts of hurting yourself or that you'd be better off dead"

If score > 0:
├── Clinical emergency
├── Requires immediate action
└── Must trigger alerts

Governance Questions:
1. Should terminology server flag critical items?
2. Should FHIR Questionnaire include criticality metadata?
3. Who validates safety algorithms?
4. How to ensure cross-site consistency?
```

### 4. MII PRO Context
```
PHQ-9 in German Hospital Setting:

Frequency:
├── Oncology: High usage (QoL tracking)
├── Psychiatry: Very high usage (diagnosis, monitoring)
├── Primary Care: Medium usage (screening)

Challenges:
├── Different scoring interpretations by specialty
├── Local modifications (added/removed items)
├── Integration with specialty-specific scales
└── Diverse patient populations (migration background)

MII Opportunity:
├── Standardize PHQ-9 across all sites
├── Establish German normative data
├── Validate Turkish-German adaptation
└── Build national PHQ-9 registry for research
```

## Comparison: PHQ-9 vs PROMIS

| Aspect | PHQ-9 | PROMIS Pain |
|--------|-------|-------------|
| **Scoring** | Sum (0-27) | IRT T-score (0-100) |
| **Complexity** | Simple | Complex |
| **Items** | Fixed 9 items | Adaptive or short form |
| **Calculation** | Any system can do it | Requires IRT libraries |
| **Clinical Use** | Direct interpretation | Needs T-score lookup |
| **Research Use** | Widely used | Growing adoption |
| **License** | Public domain | Free but trademarked |
| **Translations** | Many available | Official process |
| **MII Context** | Already widely used | New to Germany |

## Next Steps

For MII PRO implementation:

1. **Standardize PHQ-9 across sites**
   - Agree on German translation (multiple exist!)
   - Standardize scoring algorithm
   - Define clinical action thresholds

2. **Build PHQ-9 infrastructure**
   - Simpler than PROMIS (no IRT needed)
   - Good test case for MII PRO
   - Can be pilot before tackling PROMIS

3. **Extend to other simple PROMs**
   - GAD-7 (anxiety)
   - VAS scales (pain, fatigue)
   - Distress thermometer
   - Demonstrates scalability

4. **Research applications**
   - Multi-site PHQ-9 registry
   - German normative data
   - Longitudinal analysis
   - Comparative effectiveness

## Technical Implementation Priority

Suggested order for MII PRO:

```
Phase 1: PHQ-9 (Simple, High Impact)
├── 3-6 months
├── Proven clinical utility
├── No complex scoring needed
├── Good governance learning experience
└── Immediate value to sites

Phase 2: Simple PROMs (Scale Up)
├── 6-12 months
├── GAD-7, VAS scales, etc.
├── Build on PHQ-9 infrastructure
└── Demonstrate scalability

Phase 3: PROMIS (Complex, Research-Focused)
├── 12-24 months
├── Requires IRT infrastructure
├── Licensing negotiations
├── More governance overhead
└── Research-grade data
```

## Conclusion

PHQ-9 demonstrates that:
- Not all PROMs need complex infrastructure
- Simple scoring can have wide adoption
- Cross-cultural adaptation still critical
- Clinical decision support integration is key
- Governance challenges exist at all complexity levels

**Recommendation:** Start MII PRO with PHQ-9 as pilot to learn governance and technical patterns before tackling more complex instruments like PROMIS.
