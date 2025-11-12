#!/bin/bash
# Runtime installation script for ISiK Implementation Guide
# This script installs ISiK after HAPI FHIR has fully started and Hibernate Search is initialized

set -e  # Exit on error

HAPI_BASE_URL="${HAPI_BASE_URL:-http://localhost:8080/fhir}"
MAX_WAIT_SECONDS=300
CHECK_INTERVAL=5

echo "=========================================="
echo "ISiK Runtime Installation Script"
echo "=========================================="
echo "HAPI URL: $HAPI_BASE_URL"
echo ""

# Function to check if HAPI is ready
check_hapi_ready() {
    local response
    response=$(curl -s -o /dev/null -w "%{http_code}" "${HAPI_BASE_URL}/metadata" 2>/dev/null || echo "000")
    if [ "$response" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Wait for HAPI to be ready
echo "Waiting for HAPI FHIR to be ready..."
elapsed=0
while ! check_hapi_ready; do
    if [ $elapsed -ge $MAX_WAIT_SECONDS ]; then
        echo "ERROR: HAPI FHIR did not become ready within ${MAX_WAIT_SECONDS} seconds"
        exit 1
    fi
    echo "  Waiting... (${elapsed}s / ${MAX_WAIT_SECONDS}s)"
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
done

echo "✓ HAPI FHIR is ready!"
echo ""

# Additional wait to ensure Hibernate Search is fully initialized
echo "Waiting additional 30 seconds for Hibernate Search initialization..."
sleep 30
echo "✓ Hibernation Search should be initialized now"
echo ""

# Install ISiK using HAPI's $install-package operation
echo "Installing ISiK Implementation Guide 5.1.0..."
echo "  Package: de.gematik.isik"
echo "  Version: 5.1.0"
echo "  Mode: STORE_AND_INSTALL"
echo "  Fetch Dependencies: true"
echo ""

# Create the operation request
# HAPI's $install-package operation expects Parameters resource
cat > /tmp/isik-install.json <<'EOF'
{
  "resourceType": "Parameters",
  "parameter": [
    {
      "name": "name",
      "valueString": "de.gematik.isik"
    },
    {
      "name": "version",
      "valueString": "5.1.0"
    },
    {
      "name": "installMode",
      "valueString": "STORE_AND_INSTALL"
    },
    {
      "name": "reloadExisting",
      "valueBoolean": false
    },
    {
      "name": "fetchDependencies",
      "valueBoolean": true
    }
  ]
}
EOF

echo "Calling \$install-package operation..."
response=$(curl -s -X POST \
  "${HAPI_BASE_URL}/\$install-package" \
  -H "Content-Type: application/fhir+json" \
  -d @/tmp/isik-install.json \
  -w "\n%{http_code}" 2>&1)

# Extract HTTP status code (last line)
http_code=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | head -n-1)

echo ""
echo "HTTP Status: $http_code"

if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    echo "✓ ISiK installation completed successfully!"
    echo ""
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"

    # Verify installation
    echo ""
    echo "Verifying ISiK profiles are searchable..."
    verify_response=$(curl -s "${HAPI_BASE_URL}/StructureDefinition?url=https://gematik.de/fhir/isik/StructureDefinition/ISiKFormularDefinition")
    profile_count=$(echo "$verify_response" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data.get('total', 0))" 2>/dev/null || echo "0")

    if [ "$profile_count" -gt "0" ]; then
        echo "✓ ISiK profiles are searchable! Found $profile_count ISiKFormularDefinition profile(s)"
    else
        echo "⚠ Warning: ISiKFormularDefinition profile not found in search results"
        echo "   This might be expected if the profile is still being indexed"
    fi
else
    echo "✗ ISiK installation failed!"
    echo ""
    echo "Response Body:"
    echo "$response_body"
    exit 1
fi

# Cleanup
rm -f /tmp/isik-install.json

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
