# Is Server Version in the Metadata/CapabilityStatement?

**TL;DR:** ✅ **Yes, usually** - but it's optional in the FHIR spec, so some servers don't include it.

---

## 📋 FHIR R4 Specification

According to the [FHIR R4 CapabilityStatement spec](https://www.hl7.org/fhir/R4/capabilitystatement-definitions.html#CapabilityStatement.software.version):

```json
{
  "resourceType": "CapabilityStatement",
  "software": {              // ⚠️ OPTIONAL (0..1)
    "name": "...",           // Required IF software exists
    "version": "...",        // ⚠️ OPTIONAL (0..1)
    "releaseDate": "..."     // ⚠️ OPTIONAL (0..1)
  },
  "fhirVersion": "4.0.1"     // ✅ REQUIRED (1..1)
}
```

| Field | Cardinality | What It Means |
|-------|-------------|---------------|
| `software` | 0..1 | **Optional** - May or may not exist |
| `software.version` | 0..1 | **Optional** - May be missing even if `software` exists |
| `fhirVersion` | 1..1 | **Required** - Always present |

---

## 🔍 Real-World Examples

### ✅ HAPI FHIR (Includes Version)

```bash
curl http://localhost:8081/fhir/metadata
```

```json
{
  "resourceType": "CapabilityStatement",
  "software": {
    "name": "HAPI FHIR Server",
    "version": "8.4.0"          // ✅ Present!
  },
  "fhirVersion": "4.0.1",
  "implementation": {
    "description": "HAPI FHIR R4 Server",
    "url": "http://localhost:8081/fhir"
  }
}
```

### ❌ Aidbox (Does NOT Include Version)

```bash
curl http://localhost:8888/fhir/metadata
```

```json
{
  "resourceType": "CapabilityStatement",
  "software": null,             // ❌ Not present!
  "fhirVersion": "4.0.0",
  "implementation": {
    "description": "Aidbox FHIR Server"
  }
}
```

**But Aidbox does provide version elsewhere:**

```bash
curl http://localhost:8888/health
```

```json
{
  "status": "pass",
  "about": {
    "version": "2509.0",        // ✅ Version here!
    "channel": "release",
    "commit": "5aaf356b41"
  }
}
```

---

## 🎯 Server Comparison

| Server | `software.version` in `/metadata`? | Alternative Endpoint | Example |
|--------|-------------------------------------|----------------------|---------|
| **HAPI FHIR** | ✅ Yes | N/A | `GET /fhir/metadata` → `software.version: "8.4.0"` |
| **Aidbox** | ❌ No | `/health` | `GET /health` → `about.version: "2509.0"` |
| **Smile CDR** | ✅ Yes | N/A | `GET /metadata` → `software.version` |
| **Firely Server** | ✅ Usually | N/A | `GET /metadata` → `software.version` |
| **Azure FHIR** | ⚠️ Sometimes | Azure API | May show generic version |
| **AWS HealthLake** | ⚠️ Sometimes | CloudWatch | May not show specific version |

---

## 💡 Why Does This Matter?

### For Version Tracking

**Problem:** You can't reliably get server version from CapabilityStatement

**Solution:** Use Docker image tags as source of truth

```yaml
# docker-compose.test.yml
services:
  hapi-fhir-test:
    image: hapiproject/hapi:v8.4.0  # ← This is your version!
  aidbox:
    image: healthsamurai/aidboxone:2509.0  # ← This is your version!
```

### For Test Logs

Our test fixture now handles this gracefully:

```python
# From conftest.py
software = capability.get("software")
if software and isinstance(software, dict):
    server_version = software.get("version", "unknown")
else:
    # Aidbox and others may not include software.version
    server_version = "unknown (not in CapabilityStatement)"
```

**Test Output:**
```
INFO - HAPI FHIR is ready! Server version: 8.4.0, FHIR version: 4.0.1
INFO - Aidbox is ready! Server version: unknown (not in CapabilityStatement), FHIR version: 4.0.0
```

---

## 🔧 How to Get Version from Each Server

### HAPI FHIR

```bash
# Method 1: CapabilityStatement (standard FHIR)
curl -s http://localhost:8081/fhir/metadata | jq '.software.version'
# Output: "8.4.0"

# Method 2: Docker image tag
docker inspect hapi-fhir-test | grep "Image.*hapi"
# Output: hapiproject/hapi:v8.4.0
```

### Aidbox

```bash
# Method 1: Custom health endpoint
curl -s http://localhost:8888/health | jq '.about.version'
# Output: "2509.0"

# Method 2: Docker logs
docker logs aidbox-fhir-test | grep "Version:"
# Output: Version: 2509.0

# Method 3: Docker image tag
docker inspect aidbox-fhir-test | grep "Image.*aidbox"
# Output: healthsamurai/aidboxone:2509.0
```

### Smile CDR (Public Server)

```bash
# CapabilityStatement (standard FHIR)
curl -s https://try.smilecdr.com:8000/baseR4/metadata | jq '.software.version'
# Output: Version varies (public server)
```

---

## ✅ Best Practices

### ✅ DO:
- **Pin Docker image versions** (e.g., `hapiproject/hapi:v8.4.0`)
- **Use image tags as source of truth** for version tracking
- **Check `/metadata` first** (standard FHIR)
- **Have fallback methods** (logs, health endpoints, etc.)
- **Document version in FHIR_SERVER_VERSIONS.md**

### ❌ DON'T:
- **Rely solely on `software.version`** (it's optional!)
- **Use `:latest` tags** (version unknown/changes)
- **Assume all servers include version** in CapabilityStatement
- **Trust external server versions** (they can change anytime)

---

## 📊 Summary

| Question | Answer |
|----------|--------|
| **Is version in CapabilityStatement?** | Sometimes (it's optional) |
| **Can I rely on it for version tracking?** | No - use Docker image tags |
| **What about FHIR version?** | Yes - always present in `fhirVersion` field |
| **What about external servers?** | May or may not include it - use with caution |
| **Best practice for versioning?** | Pin Docker image tags (e.g., `v8.4.0`) |

---

## 🔗 References

- **FHIR R4 CapabilityStatement**: https://www.hl7.org/fhir/R4/capabilitystatement.html
- **HAPI FHIR Releases**: https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases
- **Aidbox Documentation**: https://docs.aidbox.app/overview/release-notes
- **Project Version Tracking**: `FHIR_SERVER_VERSIONS.md`

---

**Last Updated**: 2025-10-26
