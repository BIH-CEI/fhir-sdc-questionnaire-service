# Implementing the $assemble Operation in HAPI FHIR

This guide explains how to implement the `$assemble` operation for modular Questionnaires in your HAPI FHIR server.

## What is the $assemble Operation?

The `$assemble` operation takes a modular questionnaire (one that references sub-questionnaires via extensions) and produces a fully self-contained questionnaire with all content inlined.

### Example Use Case
```
Parent Questionnaire (modular)
├─ Item 1: Patient Name
├─ Item 2: [display with subQuestionnaire extension → Medical History Questionnaire]
└─ Item 3: Current Medications

After $assemble →

Assembled Questionnaire
├─ Item 1: Patient Name
├─ Item 2: Previous Diagnoses    } Content from
├─ Item 3: Allergies             } Medical History
├─ Item 4: Surgeries             } Questionnaire
└─ Item 5: Current Medications
```

## Implementation Approaches

### Option 1: Use CQF Clinical Reasoning Library (Recommended)

The **CQF Clinical Reasoning** library (https://github.com/cqframework/clinical-reasoning) provides reference implementations of FHIR Clinical Reasoning operations in Java, which may include questionnaire assembly functionality.

**Pros:**
- Pre-built, tested implementation
- Follows FHIR specifications
- Maintained by the community

**Cons:**
- Need to verify if $assemble is included
- Adds dependency to your project

**Steps:**
1. Check if the library includes `$assemble` support
2. Add the dependency to your project
3. Register the operation provider with HAPI FHIR

### Option 2: Use/Extend CQF Ruler

The **CQF Ruler** (https://github.com/cqframework/cqf-ruler) is based on HAPI FHIR JPA Server Starter and adds Clinical Reasoning Module plugins.

**Pros:**
- Built on same foundation as your project
- Full SDC support
- Production-ready

**Cons:**
- May be more than you need
- Requires understanding their plugin architecture

**Steps:**
1. Review CQF Ruler's implementation
2. Extract the $assemble operation code
3. Adapt it to your project structure

### Option 3: Custom Implementation (Most Control)

Build your own implementation from scratch following the FHIR SDC specification.

**Pros:**
- Full control over implementation
- No extra dependencies
- Tailored to your needs

**Cons:**
- More development effort
- Need to maintain and test
- Must ensure FHIR compliance

## Custom Implementation Guide

If you choose to implement `$assemble` yourself, here's how to do it:

### Step 1: Create the Operation Provider Class

Create a new Java class in your project (you'll need to set up a Java extension to the Docker setup):

```java
package your.package.provider;

import ca.uhn.fhir.jpa.api.dao.IFhirResourceDao;
import ca.uhn.fhir.rest.annotation.IdParam;
import ca.uhn.fhir.rest.annotation.Operation;
import ca.uhn.fhir.rest.annotation.OperationParam;
import ca.uhn.fhir.rest.api.server.RequestDetails;
import org.hl7.fhir.r4.model.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.Nonnull;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Component
public class QuestionnaireAssembleProvider {

    @Autowired
    private IFhirResourceDao<Questionnaire> questionnaireDao;

    /**
     * Instance-level $assemble operation
     * URL: [base]/Questionnaire/[id]/$assemble
     */
    @Operation(name = "$assemble", idempotent = true, type = Questionnaire.class)
    public Questionnaire assembleInstance(
            @IdParam IdType theId,
            RequestDetails theRequestDetails) {

        // 1. Fetch the source questionnaire
        Questionnaire source = questionnaireDao.read(theId, theRequestDetails);

        // 2. Assemble it
        return assembleQuestionnaire(source, theRequestDetails);
    }

    /**
     * Type-level $assemble operation
     * URL: [base]/Questionnaire/$assemble?questionnaire=[canonical|url]
     */
    @Operation(name = "$assemble", idempotent = true, type = Questionnaire.class)
    public Questionnaire assembleType(
            @OperationParam(name = "questionnaire") UriType theQuestionnaire,
            @OperationParam(name = "questionnaire") Questionnaire theQuestionnaireResource,
            RequestDetails theRequestDetails) {

        Questionnaire source;

        // Handle different input types
        if (theQuestionnaireResource != null) {
            source = theQuestionnaireResource;
        } else if (theQuestionnaire != null) {
            // Resolve canonical URL or resource reference
            source = resolveQuestionnaireByUrl(theQuestionnaire.getValue(), theRequestDetails);
        } else {
            throw new IllegalArgumentException("Must provide either questionnaire parameter");
        }

        return assembleQuestionnaire(source, theRequestDetails);
    }

    /**
     * Core assembly logic
     */
    private Questionnaire assembleQuestionnaire(
            @Nonnull Questionnaire source,
            @Nonnull RequestDetails theRequestDetails) {

        // Create a copy for the assembled result
        Questionnaire assembled = source.copy();

        // 1. Resolve sub-questionnaires
        List<Questionnaire.QuestionnaireItemComponent> assembledItems = new ArrayList<>();
        for (Questionnaire.QuestionnaireItemComponent item : source.getItem()) {
            assembledItems.addAll(processItem(item, theRequestDetails));
        }
        assembled.setItem(assembledItems);

        // 2. Propagate metadata from item.definition elements (if needed)
        // TODO: Implement metadata propagation

        // 3. Update assemble-expectation extension
        removeExtension(assembled, "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-assemble-expectation");

        // 4. Add assembledFrom extension
        assembled.addExtension()
            .setUrl("http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-assembledFrom")
            .setValue(new CanonicalType(source.getUrl() + "|" + source.getVersion()));

        // 5. Update version
        assembled.setVersion(UUID.randomUUID().toString());

        // 6. Optionally validate
        // TODO: Add validation if needed

        return assembled;
    }

    /**
     * Process a single item, expanding sub-questionnaires
     */
    private List<Questionnaire.QuestionnaireItemComponent> processItem(
            @Nonnull Questionnaire.QuestionnaireItemComponent item,
            @Nonnull RequestDetails theRequestDetails) {

        List<Questionnaire.QuestionnaireItemComponent> result = new ArrayList<>();

        // Check for subQuestionnaire extension
        Extension subQExt = item.getExtensionByUrl(
            "http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-subQuestionnaire"
        );

        if (subQExt != null && subQExt.getValue() instanceof CanonicalType) {
            // This is a modular reference - resolve and inline
            String subQuestionnaireUrl = ((CanonicalType) subQExt.getValue()).getValue();
            Questionnaire subQ = resolveQuestionnaireByUrl(subQuestionnaireUrl, theRequestDetails);

            if (subQ != null) {
                // Add all root items from the sub-questionnaire
                for (Questionnaire.QuestionnaireItemComponent subItem : subQ.getItem()) {
                    // Recursively process sub-items
                    result.addAll(processItem(subItem, theRequestDetails));
                }
            } else {
                throw new IllegalStateException(
                    "Could not resolve sub-questionnaire: " + subQuestionnaireUrl
                );
            }
        } else {
            // Regular item - keep it and process children
            Questionnaire.QuestionnaireItemComponent processedItem = item.copy();

            if (item.hasItem()) {
                List<Questionnaire.QuestionnaireItemComponent> processedChildren = new ArrayList<>();
                for (Questionnaire.QuestionnaireItemComponent child : item.getItem()) {
                    processedChildren.addAll(processItem(child, theRequestDetails));
                }
                processedItem.setItem(processedChildren);
            }

            result.add(processedItem);
        }

        return result;
    }

    /**
     * Resolve a Questionnaire by canonical URL or reference
     */
    private Questionnaire resolveQuestionnaireByUrl(
            String url,
            RequestDetails theRequestDetails) {

        // Parse canonical URL (may include version)
        String canonicalUrl = url;
        String version = null;
        if (url.contains("|")) {
            String[] parts = url.split("\\|");
            canonicalUrl = parts[0];
            version = parts[1];
        }

        // Search for the questionnaire
        SearchParameterMap params = new SearchParameterMap();
        params.add("url", new UriParam(canonicalUrl));
        if (version != null) {
            params.add("version", new StringParam(version));
        }

        IBundleProvider results = questionnaireDao.search(params, theRequestDetails);
        List<IBaseResource> resources = results.getResources(0, 1);

        if (resources.isEmpty()) {
            return null;
        }

        return (Questionnaire) resources.get(0);
    }

    /**
     * Remove an extension by URL
     */
    private void removeExtension(DomainResource resource, String url) {
        resource.getExtension().removeIf(ext -> url.equals(ext.getUrl()));
    }
}
```

### Step 2: Register the Operation Provider

In your HAPI FHIR JPA Server Starter configuration, register the provider:

```java
package your.package.config;

import ca.uhn.fhir.jpa.starter.AppProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import your.package.provider.QuestionnaireAssembleProvider;

@Configuration
public class FhirServerConfig {

    @Bean
    public QuestionnaireAssembleProvider questionnaireAssembleProvider() {
        return new QuestionnaireAssembleProvider();
    }
}
```

### Step 3: Update Your Docker Setup

Since you're using Docker with the official HAPI FHIR image, you'll need to:

**Option A: Create a Custom Docker Image**

Create a `Dockerfile` extending the base HAPI image:

```dockerfile
FROM hapiproject/hapi:latest

# Copy your custom JAR with the operation provider
COPY target/your-custom-operations.jar /data/hapi/plugins/

# The JAR should be a Spring Boot plugin that auto-registers
```

**Option B: Use the FastAPI Layer**

Since you already have a FastAPI layer, you could implement the assembly logic there:

```python
# api/app/services/questionnaire_assembler.py
from typing import Dict, Any, List

class QuestionnaireAssembler:
    def __init__(self, fhir_client):
        self.fhir_client = fhir_client

    def assemble(self, questionnaire_id: str) -> Dict[str, Any]:
        """Assemble a modular questionnaire"""
        # 1. Fetch source questionnaire
        source = self.fhir_client.get(f"Questionnaire/{questionnaire_id}")

        # 2. Process items recursively
        assembled = source.copy()
        assembled['item'] = self._process_items(source.get('item', []))

        # 3. Update metadata
        assembled['version'] = str(uuid.uuid4())

        # 4. Add assembledFrom extension
        assembled.setdefault('extension', []).append({
            'url': 'http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-assembledFrom',
            'valueCanonical': f"{source.get('url')}|{source.get('version')}"
        })

        return assembled

    def _process_items(self, items: List[Dict]) -> List[Dict]:
        """Process items, expanding sub-questionnaires"""
        result = []

        for item in items:
            # Check for subQuestionnaire extension
            sub_q_ext = next(
                (ext for ext in item.get('extension', [])
                 if ext['url'] == 'http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-subQuestionnaire'),
                None
            )

            if sub_q_ext:
                # Resolve and inline sub-questionnaire
                sub_q_url = sub_q_ext['valueCanonical']
                sub_q = self._resolve_questionnaire(sub_q_url)

                if sub_q:
                    # Add sub-questionnaire items
                    result.extend(self._process_items(sub_q.get('item', [])))
            else:
                # Regular item - process children recursively
                processed_item = item.copy()
                if 'item' in item:
                    processed_item['item'] = self._process_items(item['item'])
                result.append(processed_item)

        return result

    def _resolve_questionnaire(self, canonical_url: str) -> Dict[str, Any]:
        """Resolve a questionnaire by canonical URL"""
        # Parse URL and version
        if '|' in canonical_url:
            url, version = canonical_url.split('|')
            search_params = {'url': url, 'version': version}
        else:
            search_params = {'url': canonical_url}

        # Search for questionnaire
        results = self.fhir_client.search('Questionnaire', search_params)

        if results.get('total', 0) > 0:
            return results['entry'][0]['resource']

        return None
```

Then add the endpoint to your FastAPI app:

```python
# api/app/main.py
from fastapi import FastAPI, HTTPException
from .services.questionnaire_assembler import QuestionnaireAssembler
from .services.fhir_client import FHIRClient

app = FastAPI()
fhir_client = FHIRClient(base_url="http://hapi-fhir:8080/fhir")
assembler = QuestionnaireAssembler(fhir_client)

@app.post("/fhir/Questionnaire/{questionnaire_id}/$assemble")
async def assemble_questionnaire(questionnaire_id: str):
    """
    Assemble a modular questionnaire into a fully self-contained questionnaire
    """
    try:
        assembled = assembler.assemble(questionnaire_id)
        return assembled
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fhir/Questionnaire/$assemble")
async def assemble_questionnaire_type(questionnaire: dict = None, questionnaire_url: str = None):
    """
    Type-level assemble operation
    """
    if not questionnaire and not questionnaire_url:
        raise HTTPException(status_code=400, detail="Must provide questionnaire parameter")

    # Implementation similar to above
    pass
```

## Recommended Approach

For your project, I recommend **Option B (FastAPI Layer)** because:

1. You already have FastAPI in your stack
2. Python is easier to develop and debug than Java
3. No need to build custom Docker images
4. Faster iteration during development
5. You can proxy FHIR operations through FastAPI

Later, if needed, you can migrate to a Java implementation or use the CQF library.

## Testing the Implementation

Once implemented, test with:

```bash
# Create a parent questionnaire with subQuestionnaire extension
curl -X POST http://localhost:8000/fhir/Questionnaire \
  -H "Content-Type: application/fhir+json" \
  -d @parent-questionnaire.json

# Assemble it
curl -X POST http://localhost:8000/fhir/Questionnaire/[id]/$assemble

# Verify the result is fully expanded
```

## Next Steps

1. Choose your implementation approach
2. Set up the development environment
3. Implement the core assembly logic
4. Add comprehensive testing
5. Handle edge cases (circular references, missing questionnaires, etc.)
6. Add validation
7. Document the operation in your API

## References

- [SDC $assemble Specification](https://build.fhir.org/ig/HL7/sdc/OperationDefinition-Questionnaire-assemble.html)
- [SDC Modular Forms](https://hl7.org/fhir/uv/sdc/modular.html)
- [HAPI FHIR Extended Operations](https://hapifhir.io/hapi-fhir/docs/server_plain/rest_operations_operations.html)
- [CQF Clinical Reasoning](https://github.com/cqframework/clinical-reasoning)
- [CQF Ruler](https://github.com/cqframework/cqf-ruler)
