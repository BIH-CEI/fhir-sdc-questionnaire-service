# $assemble Operation Implementation Summary

## Quick Answer

To implement the `$assemble` operation in your HAPI FHIR server, you have three options:

### 1. **Python Implementation in FastAPI** ⭐ RECOMMENDED
- **Effort**: Low-Medium
- **Timeline**: 1-2 days
- **Pros**: Uses your existing FastAPI layer, easier to debug, faster iteration
- **Cons**: Not integrated directly into HAPI FHIR

### 2. **Java Custom Operation Provider**
- **Effort**: Medium-High
- **Timeline**: 3-5 days
- **Pros**: Native HAPI FHIR integration, proper FHIR operation
- **Cons**: Requires Java development, custom Docker image

### 3. **Wait for Community Implementation**
- **Effort**: None
- **Timeline**: Unknown
- **Pros**: Battle-tested, maintained by community
- **Cons**: May never happen, no control over timeline

## What We Discovered

### Current State of $assemble Support

1. **HAPI FHIR (base)**: ❌ Does NOT include `$assemble` out-of-box
2. **CQF Clinical Reasoning**: ❌ Does NOT include `$assemble` (confirmed via CQF Ruler)
3. **Public HAPI Servers**: ❌ Likely not available

### What IS Available

| Operation | HAPI FHIR | Enabled By |
|-----------|-----------|------------|
| `$populate` | ✅ | CQL enabled |
| `$extract` | ✅ | CQL enabled |
| `$package` | ✅ | CQL enabled |
| `$questionnaire` | ✅ | CQL enabled |
| `$assemble` | ❌ | **Must implement** |

## Why $assemble is Not Implemented

The `$assemble` operation is relatively complex and less commonly used than `$populate` and `$extract`. Most systems either:
- Don't use modular questionnaires
- Assemble questionnaires at authoring time, not runtime
- Use proprietary assembly mechanisms

## Implementation Complexity

### Core Algorithm (from SDC spec):
1. Resolve sub-questionnaires from extensions
2. Propagate metadata from definitions
3. Update assembly-expectation extension
4. Add assembledFrom lineage tracking
5. Update version
6. Validate results

### Key Challenges:
- **Recursive resolution**: Sub-questionnaires may contain sub-questionnaires
- **Error handling**: Missing references, circular dependencies
- **Metadata propagation**: Merging element definitions
- **Version management**: Tracking assembled versions
- **Performance**: Caching resolved questionnaires

## Recommended Implementation Path

Based on your architecture, here's the recommended approach:

### Phase 1: FastAPI Prototype (Week 1)
1. Implement basic assembly in Python (see `IMPLEMENTING_ASSEMBLE_OPERATION.md`)
2. Handle simple one-level sub-questionnaire expansion
3. Test with sample questionnaires
4. Expose via FastAPI endpoint

### Phase 2: Enhancement (Week 2-3)
1. Add recursive sub-questionnaire resolution
2. Implement metadata propagation
3. Add error handling and validation
4. Add caching for performance

### Phase 3: Production Hardening (Week 4)
1. Add comprehensive testing
2. Handle edge cases (circular refs, missing questionnaires)
3. Add monitoring and logging
4. Document API and usage

### Phase 4: Optional - Java Migration (Later)
If needed for performance or integration:
1. Port Python logic to Java
2. Create HAPI operation provider
3. Build custom Docker image
4. Deploy and test

## Quick Start: Minimal Python Implementation

See the detailed implementation in `IMPLEMENTING_ASSEMBLE_OPERATION.md`, but here's the essence:

```python
def assemble_questionnaire(source_questionnaire: dict) -> dict:
    """
    Minimal viable implementation of $assemble
    """
    assembled = source_questionnaire.copy()

    # Process each item recursively
    assembled['item'] = process_items(source_questionnaire.get('item', []))

    # Update version
    assembled['version'] = f"{assembled.get('version', '1.0.0')}-assembled"

    # Add lineage
    assembled.setdefault('extension', []).append({
        'url': 'http://hl7.org/fhir/uv/sdc/StructureDefinition/sdc-questionnaire-assembledFrom',
        'valueCanonical': f"{source_questionnaire['url']}|{source_questionnaire.get('version')}"
    })

    return assembled

def process_items(items: list) -> list:
    """
    Recursively process items, expanding sub-questionnaires
    """
    result = []
    for item in items:
        # Check for subQuestionnaire extension
        sub_q_ext = find_extension(item, 'sdc-questionnaire-subQuestionnaire')

        if sub_q_ext:
            # Resolve and inline sub-questionnaire
            sub_q = fetch_questionnaire(sub_q_ext['valueCanonical'])
            result.extend(process_items(sub_q['item']))
        else:
            # Keep item, process children
            if 'item' in item:
                item['item'] = process_items(item['item'])
            result.append(item)

    return result
```

## Decision Matrix

| Factor | FastAPI | Java | Wait |
|--------|---------|------|------|
| Time to implement | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| Development effort | ⭐⭐⭐ | ⭐ | ⭐⭐⭐ |
| Maintenance | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| FHIR compliance | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Flexibility | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| Integration | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

⭐⭐⭐ = Excellent, ⭐⭐ = Good, ⭐ = Poor

## Files Created

1. `SDC_CONFIGURATION.md` - How to enable SDC support (DONE ✅)
2. `IMPLEMENTING_ASSEMBLE_OPERATION.md` - Detailed implementation guide (DONE ✅)
3. `ASSEMBLE_OPERATION_SUMMARY.md` - This file (DONE ✅)

## Next Steps

1. **Decision**: Choose implementation approach (FastAPI recommended)
2. **Setup**: Test SDC configuration on Docker-enabled machine
3. **Verify**: Confirm `$populate` and `$extract` work with CQL enabled
4. **Implement**: Start with minimal Python implementation
5. **Test**: Create sample modular questionnaires
6. **Iterate**: Enhance based on testing results

## Questions to Consider

1. **Do you actually need $assemble?**
   - Can you assemble questionnaires at authoring time instead?
   - Are your questionnaires truly modular?

2. **What's your use case?**
   - Form libraries with reusable sections?
   - Dynamic questionnaire composition?
   - Integration with form builders?

3. **What's your timeline?**
   - Urgent: Go with FastAPI
   - Flexible: Consider Java implementation
   - No rush: Wait for community

## Support Resources

- SDC Spec: https://build.fhir.org/ig/HL7/sdc/OperationDefinition-Questionnaire-assemble.html
- HAPI Operations: https://hapifhir.io/hapi-fhir/docs/server_plain/rest_operations_operations.html
- Your Implementation Guide: `IMPLEMENTING_ASSEMBLE_OPERATION.md`

## Conclusion

The `$assemble` operation is **not available out-of-box** in HAPI FHIR and **must be implemented**. The FastAPI approach offers the quickest path to a working solution, with the option to migrate to Java later if needed.
