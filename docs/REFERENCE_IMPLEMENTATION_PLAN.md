# MII PRO Reference Implementation Plan

**Goal:** Reduce PROM implementation costs to near-zero through open-source, plug-and-play components

---

## Vision

Instead of every MII site building their own PROM infrastructure, provide a complete, tested, production-ready reference implementation that sites can deploy in **1 day, not 6 months**.

```
Current State (2024):
├─ Each site builds own solution
├─ 6-12 months implementation
├─ €100-500k per site
├─ Incompatible implementations
└─ No shared learnings

Target State (2025):
├─ Deploy reference implementation
├─ 1 day setup
├─ €0 implementation cost (just hosting)
├─ 100% compatible across sites
└─ Community-driven improvements
```

---

## Core Principle: Radical Simplicity

**Every component must be:**
1. **Plug-and-play:** `docker compose up` or `npm install`
2. **Zero-config default:** Works out of box, customize optionally
3. **Standards-based:** Only FHIR, no proprietary formats
4. **Open-source:** Apache 2.0, community-driven
5. **Production-ready:** Tests, docs, support

---

## Architecture Components

### 1. MII PRO Terminology Service

**Repository:** `mii-pro/terminology-service`

**What it does:**
- Wraps ONTOSERVER (or any FHIR terminology server)
- Adds missing LOINC APIs (Panel → Questionnaire, Ordinals)
- Multi-language with fallback logic
- Version-aware ValueSet expansion
- Translation status tracking

**Deployment:**
```yaml
# docker-compose.yml
services:
  terminology:
    image: ghcr.io/mii-pro/terminology-service:latest
    environment:
      UPSTREAM_TERMINOLOGY_SERVER: http://ontoserver:8080/fhir
      CACHE_ENABLED: true
    ports:
      - "3000:3000"
```

**Implementation Cost:** €0 (just deploy)
**Maintenance:** Community-driven

---

### 2. MII PRO Scoring Service

**Repository:** `mii-pro/scoring-service`

**What it does:**
- Simple sum scoring (PHQ-9, GAD-7, VAS, etc.)
- PROMIS IRT scoring (requires PROMIS license, optional)
- Implements FHIR $extract operation
- Creates Observations from QuestionnaireResponses
- Validates responses against expected ranges

**Deployment:**
```yaml
services:
  scoring:
    image: ghcr.io/mii-pro/scoring-service:latest
    environment:
      # Simple scoring: Always enabled (open source)
      ENABLE_SIMPLE_SCORING: true

      # PROMIS IRT: Optional (requires license)
      # ENABLE_PROMIS_IRT: true
      # PROMIS_LICENSE_KEY: your-key
    ports:
      - "8090:8080"
```

**Scoring Algorithms:**
```python
# Open source (Apache 2.0):
- PHQ-9: Sum score (0-27)
- GAD-7: Sum score (0-21)
- Distress Thermometer: Single item (0-10)
- VAS scales: Direct value (0-100)

# Optional (requires PROMIS license):
- PROMIS IRT T-scores
- CAT (Computer Adaptive Testing)
```

**Implementation Cost:** €0 for simple scoring, €10-50k/year for PROMIS license (optional)

---

### 3. MII PRO Questionnaire Renderer

**Repository:** `mii-pro/questionnaire-renderer`

**What it does:**
- React component for FHIR Questionnaires
- Multi-language support with automatic terminology lookup
- SMART on FHIR integration
- Accessibility (WCAG 2.1 AA)
- Mobile-responsive

**Usage:**
```bash
npm install @mii-pro/questionnaire-renderer
```

```jsx
import { QuestionnaireRenderer } from '@mii-pro/questionnaire-renderer';

<QuestionnaireRenderer
  questionnaire={questionnaireResource}
  language="de-DE"
  terminologyServer="http://localhost:3000/fhir"
  onSubmit={handleSubmit}
/>
```

**Built on:**
- LHC-Forms (NLM's proven renderer)
- Enhanced with MII-specific features
- Drop-in replacement, zero config

**Implementation Cost:** €0 (npm install)

---

### 4. HAPI FHIR Plugins

**Repository:** `mii-pro/hapi-plugins`

**What it does:**
- Version Detection Interceptor (warns about mismatches)
- Translation Fallback Handler (automatic language fallback)
- Auto-Scoring Interceptor (calls scoring service on QuestionnaireResponse create)
- Terminology Cache Warmer (pre-loads common ValueSets)

**Installation:**
```java
// Drop JAR into HAPI's lib directory
// Or configure in hapi.properties:
hapi.custom.interceptors=de.mii.pro.interceptors.VersionDetectionInterceptor
```

**Implementation Cost:** €0 (drop-in JAR)

---

### 5. FHIR Packages

**Published to:** Simplifier.net/packages.fhir.org

**Packages:**

#### `de.mii.pro.questionnaires`
- All validated questionnaires (PROMIS, PHQ-9, GAD-7, etc.)
- German translations included
- Metadata: validation status, version, source

#### `de.mii.pro.scoring`
- CQL Libraries for scoring algorithms
- ObservationDefinitions for results
- Pre-validated, ready to use

#### `de.mii.pro.terminology`
- German ValueSets
- Translation provenance
- Version mappings

**Installation:**
```yaml
# hapi.properties or application.yaml
implementationguides:
  mii_pro_questionnaires:
    name: de.mii.pro.questionnaires
    version: 1.0.0
    installMode: STORE_AND_INSTALL
```

**Implementation Cost:** €0 (HAPI auto-installs)

---

## Reference Deployment Architecture

```yaml
# Complete MII PRO Stack
# Deploy time: 30 minutes
# Prerequisites: Docker, 8GB RAM

version: '3.8'

services:
  # Your existing HAPI FHIR (with plugins)
  hapi:
    image: hapiproject/hapi:latest
    volumes:
      - ./mii-pro-plugins:/app/extra-lib  # Drop-in JARs
      - ./config:/app/config
    environment:
      # Point to MII PRO services
      mii.terminology.url: http://terminology:3000/fhir
      mii.scoring.url: http://scoring:8080

  # MII PRO Terminology Service
  terminology:
    image: ghcr.io/mii-pro/terminology-service:latest
    environment:
      UPSTREAM_TERMINOLOGY_SERVER: http://your-ontoserver/fhir

  # MII PRO Scoring Service
  scoring:
    image: ghcr.io/mii-pro/scoring-service:latest
    environment:
      ENABLE_SIMPLE_SCORING: true

  # Optional: MII PRO UI (sample frontend)
  ui:
    image: ghcr.io/mii-pro/sample-ui:latest
    ports:
      - "80:80"
```

**Total Cost:** €0 (implementation), ~€50-100/month (hosting)

---

## Implementation Timeline

### Phase 1: Foundation (Months 1-3)
**Goal:** MVP that sites can deploy

**Deliverables:**
1. Terminology Service (production-ready)
   - LOINC Panel API
   - Ordinal values support
   - Multi-language fallback

2. Simple Scoring Service
   - PHQ-9, GAD-7 sum scores
   - FHIR $extract implementation
   - Docker deployment

3. FHIR Packages
   - PHQ-9 + GAD-7 questionnaires
   - German translations
   - CQL scoring libraries

4. Documentation
   - Deployment guides
   - API documentation
   - Troubleshooting

**Pilot Sites:** 2-3 sites test MVP

---

### Phase 2: Production Hardening (Months 4-6)
**Goal:** Production-grade, scalable

**Deliverables:**
1. Questionnaire Renderer Component
   - React npm package
   - SMART on FHIR integration
   - Mobile-responsive

2. HAPI Plugins
   - Version detection
   - Auto-scoring
   - Easy installation

3. Expanded Package Library
   - More questionnaires (10+)
   - More languages
   - Versioned releases

4. Operations Support
   - Monitoring/alerting
   - Automated tests
   - CI/CD pipelines

**Pilot Sites:** 5-10 sites in production

---

### Phase 3: Advanced Features (Months 7-12)
**Goal:** Complete ecosystem

**Deliverables:**
1. PROMIS IRT Scoring (if licensed)
2. Translation Management Portal
3. Questionnaire Repository UI
4. Analytics/Reporting Module
5. HL7 Submissions (if needed)

**Target:** All MII sites can deploy

---

## Cost Model: Community vs Commercial

### Community Edition (Free, Open Source)
```
Included:
✅ Terminology Service (all features)
✅ Simple Scoring (PHQ-9, GAD-7, VAS, etc.)
✅ Questionnaire Renderer
✅ HAPI Plugins
✅ FHIR Packages (basic questionnaires)
✅ Community Support (GitHub Issues)

Cost: €0
License: Apache 2.0
Support: Best-effort community
```

### Commercial Support (Optional)
```
Additional Services:
✅ Professional support (SLA)
✅ Custom questionnaire development
✅ Site-specific integrations
✅ Training workshops
✅ PROMIS IRT licensing (pass-through)

Cost: €5-20k/year per site
Provider: MII Coordination or commercial partner
```

**Key Principle:** Core functionality always free and open!

---

## Governance Model

### Technical Steering Committee
- 5-7 members
- Mix: MII sites, developers, clinical informaticians
- Decides: Roadmap, features, standards

### Working Groups
- **Terminology WG:** ValueSet curation, translations
- **Scoring WG:** Algorithm validation, new instruments
- **Integration WG:** EHR integration patterns

### Contribution Model
- Open GitHub repositories
- Pull requests welcome
- Code review by maintainers
- Quarterly releases

---

## Success Metrics

### Adoption
- **Target Year 1:** 10 MII sites using reference implementation
- **Target Year 2:** 25+ sites, 50% of MII
- **Target Year 3:** Standard deployment for all new sites

### Cost Reduction
- **Current:** €100-500k per site implementation
- **With Reference Implementation:** €0 implementation + €1-5k deployment
- **Savings:** €2-5M across MII consortium (Year 1)

### Interoperability
- **Current:** Each site different implementation
- **Target:** 100% compatible QuestionnaireResponses across sites
- **Enable:** Multi-site studies, data pooling, federated analysis

---

## Communication Strategy

### Workshop (Next Week)
**Message:**
1. "Here are the problems" (Demo scenarios)
2. "Here's the solution we're building" (Reference implementation)
3. "Join us as pilot site" (Recruitment)

**Outcomes:**
- 5-10 sites commit to pilot
- 2-3 developers volunteer
- Funding commitment (MII core budget)

### Post-Workshop
1. **GitHub Organization:** `github.com/mii-pro`
2. **Regular Calls:** Monthly tech sync
3. **Documentation:** docs.mii-pro.de
4. **Slack/Discord:** Community chat

---

## Funding Model

### Initial Development (Year 1)
```
€250-400k total:
├─ €150k: Core development (2 FTE developers)
├─ €50k: Testing/QA
├─ €30k: Documentation
├─ €20k: Infrastructure (GitHub, CI/CD)
└─ €50k: Contingency

Sources:
├─ MII Core Budget
├─ BMBF Project Funding
└─ Site contributions (optional)
```

### Ongoing (Year 2+)
```
€100-150k/year:
├─ €80k: Maintenance (1 FTE)
├─ €30k: Infrastructure
├─ €20k: Community events
└─ €20k: New features

Sources:
├─ MII Core Budget
└─ Optional: Commercial support revenue
```

**Key:** Core team tiny (1-2 FTE), community does the rest!

---

## Risk Mitigation

### Risk: Low Adoption
**Mitigation:**
- Start with motivated pilot sites
- Make deployment REALLY easy
- Show immediate value (cost savings)

### Risk: Technical Complexity
**Mitigation:**
- Use proven components (HAPI, LHC-Forms)
- Avoid reinventing wheels
- Focus on "glue code" not new platforms

### Risk: Governance Overhead
**Mitigation:**
- Light governance (no heavy processes)
- Decisions by doing (code > committees)
- BDFL model if needed (benevolent dictator)

### Risk: Commercial Competition
**Mitigation:**
- Apache 2.0 license (commercial-friendly)
- Allow commercial support offerings
- Core always free (no bait-and-switch)

---

## Why This Will Work

1. **Proven Model:** Linux, Kubernetes, OpenMRS all work this way
2. **Clear Value:** €500k → €0 implementation cost
3. **MII Alignment:** Fits MII mission (standardization, interoperability)
4. **Community Ready:** Developers exist, need coordination
5. **Small Core:** 1-2 FTE maintainers, community contributes

---

## Call to Action (Workshop)

**For Sites:**
> "Stop building your own. Deploy ours instead. Save €500k. Deploy in 1 day."

**For Developers:**
> "Contribute once. Benefit 30+ sites. Build something that matters."

**For Governance:**
> "Fund small core team. Enable community. Save millions across MII."

**For Users (Clinicians):**
> "Same PRO experience at every MII site. Data finally comparable."

---

## Next Steps (Immediate)

1. **Workshop Presentation:**
   - Show problems (current workshop scenarios)
   - Present solution (this reference implementation plan)
   - Recruit pilot sites (5-10 commitments)

2. **Post-Workshop (Week 1):**
   - Create GitHub organization
   - Set up infrastructure (CI/CD, docs)
   - Form technical steering committee

3. **Month 1:**
   - Start Phase 1 development
   - Weekly pilot site sync
   - First code commits

4. **Month 3:**
   - MVP deployment at 2-3 pilot sites
   - Gather feedback
   - Iterate

---

## Vision: 2026

Every MII site:
```bash
# Set up complete PRO infrastructure in 30 minutes:

git clone https://github.com/mii-pro/deployment
cd deployment
docker compose up -d

# Done.
# ✅ Terminology service running
# ✅ Scoring service running
# ✅ HAPI configured with plugins
# ✅ 20+ questionnaires ready to use
# ✅ Multi-language support
# ✅ Compatible with all other MII sites
```

**Total cost:** €0 (implementation) + €50/month (hosting)

**Alternative (current):** €300k + 9 months + incompatible result

---

**The Reference Implementation IS the Standard.**

Not a spec to implement. Not a guideline to follow.
Just: `docker compose up`. That's it.

---

**Questions for Workshop Participants:**

1. Would you deploy this at your site? (Yes/No)
2. Would you contribute code/testing? (Yes/No)
3. How much would this save your site? (€50k, €200k, €500k?)
4. What's missing from this plan?

---

**Let's build it together.**

Contact: [Workshop Organizer]
GitHub: github.com/mii-pro (coming soon)
