# Multi-Server Testing Guide

This test suite is **server-agnostic** and can run against any FHIR R4 server (HAPI, Aidbox, Azure, Firely, etc.).

## Quick Start

### Test Against HAPI FHIR (default)
```bash
cd api
pytest tests/ -v
```

### Test Against Other Servers
```bash
# Aidbox
pytest tests/ --fhir-server=aidbox -v

# Firely Server
pytest tests/ --fhir-server=firely -v

# Azure Health Data Services
export AZURE_FHIR_URL=https://your-fhir.azurehealthcareapis.com
pytest tests/ --fhir-server=azure -v

# Smile CDR (public demo server - read-only tests)
pytest tests/ --fhir-server=smile -v

# Custom server
pytest tests/ --fhir-url=http://custom-server:8080/fhir -v
```

## Supported FHIR Servers

| Server | Flag | Default URL | Validation | Notes |
|--------|------|-------------|------------|-------|
| **HAPI FHIR** | `hapi` | `localhost:8081/fhir` | Lenient | Default, good for development |
| **Aidbox** | `aidbox` | `localhost:8888` | Strict | Fast, PostgreSQL-based (requires license) |
| **Firely Server** | `firely` | `localhost:4080` | Strict | Enterprise-grade |
| **Azure** | `azure` | Env: `AZURE_FHIR_URL` | Strict | Cloud, requires auth |
| **Smile CDR** | `smile` | `try.smilecdr.com:8000/baseR4` | Strict | Public demo server (read-only) |

## Server Setup

### HAPI FHIR (Included)
```bash
docker-compose -f docker-compose.test.yml up -d
pytest tests/ --fhir-server=hapi -v
```

### Smile CDR (Public Demo Server)
```bash
# No setup needed - uses public demo server
pytest tests/ --fhir-server=smile -v
```

**Note**: This is a **read-only** public server. Tests that create/update/delete resources will be skipped automatically.

### Aidbox (Local Setup - Optional)
**Status**: ⚠️ Not yet set up (configuration exists, but no docker-compose file)

To set up Aidbox locally, you need:
1. An Aidbox license (free dev license available at https://aidbox.app)
2. Create `docker-compose.aidbox.yml`:

```yaml
version: '3.8'
services:
  aidbox:
    image: healthsamurai/aidboxone:latest
    container_name: aidbox-fhir-test
    ports:
      - "8888:8888"
    environment:
      AIDBOX_LICENSE: ${AIDBOX_LICENSE}
      AIDBOX_ADMIN_PASSWORD: password
      AIDBOX_FHIR_VERSION: 4.0.0
    depends_on:
      - aidbox-db

  aidbox-db:
    image: postgres:14
    container_name: aidbox-db
    environment:
      POSTGRES_DB: aidbox
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
```

```bash
export AIDBOX_LICENSE=your-license-key
docker-compose -f docker-compose.aidbox.yml up -d
pytest tests/ --fhir-server=aidbox -v
```

### Firely Server
```bash
# docker-compose.firely.yml
version: '3'
services:
  firely:
    image: fire.ly/server:latest
    ports:
      - "4080:4080"
    environment:
      FHIRSERVER_SQLSERVER__ConnectionString: "..."
```

```bash
docker-compose -f docker-compose.firely.yml up -d
pytest tests/ --fhir-server=firely -v
```

## Server Profiles

Each server has a profile in `tests/conftest.py` defining behavior:

```python
SERVER_PROFILES = {
    "hapi": {
        "name": "HAPI FHIR",
        "base_url": "http://localhost:8081/fhir",
        "validation_strict": False,  # Lenient
        "supports_xml": True,
        "supports_graphql": False,
        "startup_timeout": 120,
    },
    "aidbox": {
        "name": "Aidbox",
        "validation_strict": True,  # Strict validation
        "supports_graphql": True,   # GraphQL API
        # ...
    }
}
```

## Writing Server-Agnostic Tests

### Use `fhir_server` Fixture
```python
async def test_my_feature(fhir_server):
    """Works with any FHIR server."""
    response = await fhir_server.get("/Questionnaire")
    assert response.status_code == 200
```

### Handle Server Differences
```python
async def test_validation(fhir_server, server_profile):
    """Adapt to server behavior."""
    invalid = {"resourceType": "Questionnaire", "item": []}
    response = await fhir_server.post("/Questionnaire", json=invalid)

    if server_profile["validation_strict"]:
        # Strict servers (Aidbox, Azure) reject invalid resources
        assert response.status_code in [400, 422]
    else:
        # Lenient servers (HAPI) may accept it
        assert response.status_code in [200, 201, 400, 422]
```

### Check Feature Support
```python
@pytest.mark.skipif(
    not server_profile.get("supports_graphql"),
    reason="Server doesn't support GraphQL"
)
async def test_graphql_query(fhir_server):
    """Only runs on servers with GraphQL support."""
    query = "{ Questionnaire { id title } }"
    response = await fhir_server.post("/graphql", json={"query": query})
    assert response.status_code == 200
```

## CI/CD Multi-Server Matrix

### GitHub Actions Example
```yaml
name: Multi-Server SDC Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        fhir-server: [hapi, aidbox, firely]

    steps:
      - uses: actions/checkout@v3

      - name: Start ${{ matrix.fhir-server }}
        run: |
          docker-compose -f docker-compose.${{ matrix.fhir-server }}.yml up -d

      - name: Run Tests
        run: |
          cd api
          pip install -r requirements.txt -r requirements-test.txt
          pytest tests/ --fhir-server=${{ matrix.fhir-server }} \
            --junitxml=results-${{ matrix.fhir-server }}.xml

      - name: Upload Results
        uses: actions/upload-artifact@v3
        with:
          name: test-results-${{ matrix.fhir-server }}
          path: api/results-*.xml
```

## Migration from HAPI-Only Tests

The suite maintains **backward compatibility**:

- `hapi_client` fixture → Still works (deprecated, use `fhir_server`)
- Default server → HAPI FHIR
- Existing tests → Run unchanged

### Gradual Migration
```python
# Old (still works)
async def test_old(hapi_client):
    response = await hapi_client.get("/metadata")

# New (preferred)
async def test_new(fhir_server):
    response = await fhir_server.get("/metadata")
```

## Troubleshooting

### Server Not Ready
```bash
# Check if server is running
docker ps

# View server logs
docker logs hapi-fhir-test
docker logs aidbox

# Increase timeout in SERVER_PROFILES
```

### Test Fails on Different Server
```python
# Use server_profile to adapt behavior
if server_profile["validation_strict"]:
    assert response.status_code == 400
else:
    assert response.status_code in [200, 400]
```

### Custom Server
```bash
# Override URL
pytest tests/ --fhir-url=http://192.168.1.100:8080/fhir -v

# Set via environment
export FHIR_BASE_URL=http://192.168.1.100:8080/fhir
pytest tests/ -v
```

## Benefits of Multi-Server Testing

✅ **Validates SDC Compliance** - Not just "works with HAPI"
✅ **Finds Edge Cases** - Different servers interpret specs differently
✅ **Ensures Portability** - Can switch servers without breaking
✅ **Provides Comparison** - Performance, features, strictness
✅ **Industry Standard** - Test against production-grade servers

## Next Steps

1. **Add more servers** - Edit `SERVER_PROFILES` in `conftest.py`
2. **Server-specific tests** - Use `server_profile` fixture
3. **CI/CD matrix** - Test all servers automatically
4. **Performance comparison** - Benchmark across servers

## Resources

- [HAPI FHIR](https://hapifhir.io/)
- [Aidbox](https://www.health-samurai.io/aidbox)
- [Firely Server](https://fire.ly/products/firely-server/)
- [Azure Health Data Services](https://azure.microsoft.com/en-us/products/health-data-services)
