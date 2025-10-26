# FHIR Test Server Versions

This document tracks the versions of FHIR servers used for testing to ensure reproducibility and stability.

---

## Current Versions

| Server | Image | Version | FHIR Version | Last Updated | Notes |
|--------|-------|---------|--------------|--------------|-------|
| **HAPI FHIR** | `hapiproject/hapi:v8.4.0` | 8.4.0 | R4 (4.0.1) | 2025-10-26 | Stable, lenient validation |
| **Aidbox** | `healthsamurai/aidboxone:2509.0` | 2509.0 | R4 (4.0.0) | 2025-10-26 | Strict validation, fast |
| **Smile CDR** | Public Server | Unknown | R4 | - | Public demo, read-only |
| **PostgreSQL (HAPI)** | `postgres:14` | 14 | - | - | Stable LTS version |
| **PostgreSQL (Aidbox)** | `postgres:14` | 14 | - | - | Stable LTS version |

---

## Version Update Policy

### When to Update

✅ **Update when:**
- Security vulnerabilities are announced
- Critical bugs are fixed
- New SDC features need testing
- Quarterly version reviews (every 3 months)

❌ **Don't update during:**
- Active development sprints
- Right before releases
- When test suite is unstable

### Update Process

1. **Check for new versions:**
   ```bash
   # HAPI FHIR releases
   # https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases

   # Aidbox releases
   # https://docs.aidbox.app/overview/release-notes
   ```

2. **Test new version locally:**
   ```bash
   # Pull new version
   docker pull hapiproject/hapi:v8.5.0

   # Update docker-compose (create backup first)
   cp docker-compose.test.yml docker-compose.test.yml.bak

   # Edit docker-compose.test.yml
   # image: hapiproject/hapi:v8.5.0

   # Restart and test
   docker-compose -f docker-compose.test.yml down
   docker-compose -f docker-compose.test.yml up -d
   cd api && pytest tests/ -v
   ```

3. **If tests pass:**
   - Update this VERSION.md file
   - Commit the docker-compose changes
   - Update CI/CD (if applicable)
   - Notify team

4. **If tests fail:**
   - Document failures
   - Decide: Fix tests OR stay on current version
   - Create issue to track

---

## Checking Current Versions

### Running Containers

```bash
# Check HAPI version (from CapabilityStatement)
curl -s http://localhost:8081/fhir/metadata | jq '.software.version'
# Output: "8.4.0"

# Check Aidbox version (NOT in CapabilityStatement - use /health endpoint)
curl -s http://localhost:8888/health | jq '.about.version'
# Output: "2509.0"

# Alternative: Check Aidbox version from logs
docker logs aidbox-fhir-test | grep "Version:"

# Check image versions
docker images | grep -E "(hapi|aidbox)"

# Check running container versions
docker ps --format "table {{.Names}}\t{{.Image}}"
```

### Why Different Endpoints?

**FHIR R4 Specification:**
- `CapabilityStatement.software.version` is **OPTIONAL**
- `CapabilityStatement.fhirVersion` is **REQUIRED**

**Server Implementations:**

| Server | Includes `software.version`? | Alternative Endpoint |
|--------|------------------------------|---------------------|
| **HAPI FHIR** | ✅ Yes | `/metadata` (standard FHIR) |
| **Aidbox** | ❌ No | `/health` (custom endpoint) |
| **Smile CDR** | ✅ Yes | `/metadata` (standard FHIR) |
| **Firely** | ✅ Usually | `/metadata` (standard FHIR) |
| **Azure FHIR** | ⚠️ Sometimes | `/metadata` (may be generic) |

**Recommendation:** Don't rely solely on `software.version` - use Docker image tags as source of truth.

### Available Versions

```bash
# List available HAPI tags
curl -s https://hub.docker.com/v2/repositories/hapiproject/hapi/tags | jq -r '.results[].name' | head -10

# List available Aidbox tags (requires authentication)
curl -s https://hub.docker.com/v2/repositories/healthsamurai/aidboxone/tags | jq -r '.results[].name' | head -10
```

---

## Version History

| Date | Server | Old Version | New Version | Reason | Test Impact |
|------|--------|-------------|-------------|--------|-------------|
| 2025-10-26 | HAPI | `latest` | `v8.4.0` | Pin version for reproducibility | ✅ All pass |
| 2025-10-26 | Aidbox | `latest` | `2509.0` | Pin version for reproducibility | ⚠️ 5/7 metadata tests pass |

---

## External Test Servers

### Smile CDR (Public)

- **URL**: `https://try.smilecdr.com:8000/baseR4`
- **Version**: Unknown (public server, version may change)
- **Update Policy**: No control - accept version changes
- **Mitigation**: Mark tests as `@pytest.mark.flaky` if they depend on Smile CDR

### Future Servers

| Server | Status | Version Control |
|--------|--------|-----------------|
| **Firely** | Not configured | Would need license + pinned version |
| **Azure FHIR** | Not configured | Cloud service, version controlled by Microsoft |
| **AWS HealthLake** | Not configured | Cloud service, version controlled by AWS |

---

## FHIR Version Compatibility

| FHIR Version | Status | Notes |
|--------------|--------|-------|
| **R4 (4.0.1)** | ✅ Primary | HAPI default |
| **R4 (4.0.0)** | ✅ Supported | Aidbox |
| R5 | ❌ Not tested | Future consideration |
| STU3 | ❌ Not supported | Legacy |

---

## CI/CD Considerations

### Docker Image Caching

```yaml
# .github/workflows/test.yml
- name: Pull Docker images with caching
  run: |
    docker pull hapiproject/hapi:v8.4.0
    docker pull healthsamurai/aidboxone:2509.0
```

### Version Verification

```yaml
- name: Verify FHIR server versions
  run: |
    docker run --rm hapiproject/hapi:v8.4.0 --version || true
    # Add version checks here
```

---

## Troubleshooting

### Problem: Docker pull gets wrong version

```bash
# Force pull specific version
docker pull hapiproject/hapi:v8.4.0 --no-cache

# Verify image
docker images hapiproject/hapi
```

### Problem: Tests fail after version update

```bash
# Check what changed
docker run --rm hapiproject/hapi:v8.4.0 cat /app/CHANGELOG.md

# Rollback to previous version
docker-compose -f docker-compose.test.yml down
# Edit docker-compose.test.yml back to old version
docker-compose -f docker-compose.test.yml up -d
```

### Problem: Multiple versions installed locally

```bash
# Clean up old images
docker images | grep hapi
docker rmi hapiproject/hapi:latest
docker rmi <image-id>

# Keep only pinned versions
docker images | grep "v8.4.0\|2509.0"
```

---

## References

- **HAPI FHIR Releases**: https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases
- **Aidbox Release Notes**: https://docs.aidbox.app/overview/release-notes
- **FHIR R4 Spec**: https://www.hl7.org/fhir/R4/
- **Docker Hub - HAPI**: https://hub.docker.com/r/hapiproject/hapi
- **Docker Hub - Aidbox**: https://hub.docker.com/r/healthsamurai/aidboxone

---

**Last Updated**: 2025-10-26
**Maintained By**: Development Team
