#!/bin/bash
# Check FHIR server versions and compare with available updates
#
# Usage:
#   ./scripts/check-server-versions.sh

set -e

echo "=================================================="
echo "FHIR Test Server Version Checker"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
if ! command_exists docker; then
    echo -e "${RED}Error: docker not found${NC}"
    exit 1
fi

if ! command_exists jq; then
    echo -e "${YELLOW}Warning: jq not found (optional, for better JSON parsing)${NC}"
fi

echo "📋 Current Pinned Versions (from docker-compose files):"
echo "--------------------------------------------------------"

# HAPI version from docker-compose.test.yml
HAPI_PINNED=$(grep -A 1 "hapi-fhir-test:" docker-compose.test.yml | grep "image:" | awk -F: '{print $3}')
echo -e "HAPI FHIR:  ${GREEN}${HAPI_PINNED}${NC}"

# Aidbox version from docker-compose.aidbox.yml
AIDBOX_PINNED=$(grep -A 1 "aidbox:" docker-compose.aidbox.yml | grep "image:" | awk -F: '{print $3}')
echo -e "Aidbox:     ${GREEN}${AIDBOX_PINNED}${NC}"

echo ""
echo "🏃 Running Versions (from containers):"
echo "--------------------------------------------------------"

# Check if HAPI is running
if docker ps --format '{{.Names}}' | grep -q "hapi-fhir-test"; then
    HAPI_RUNNING=$(curl -s http://localhost:8081/fhir/metadata 2>/dev/null | grep -o '"version":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    if [ "$HAPI_RUNNING" != "unknown" ]; then
        echo -e "HAPI FHIR:  ${GREEN}v${HAPI_RUNNING}${NC} (running)"
    else
        echo -e "HAPI FHIR:  ${YELLOW}running but version unknown${NC}"
    fi
else
    echo -e "HAPI FHIR:  ${RED}not running${NC}"
fi

# Check if Aidbox is running
if docker ps --format '{{.Names}}' | grep -q "aidbox-fhir-test"; then
    AIDBOX_RUNNING=$(docker logs aidbox-fhir-test 2>&1 | grep "Version:" | tail -1 | awk '{print $3}' || echo "unknown")
    if [ "$AIDBOX_RUNNING" != "unknown" ]; then
        echo -e "Aidbox:     ${GREEN}${AIDBOX_RUNNING}${NC} (running)"
    else
        echo -e "Aidbox:     ${YELLOW}running but version unknown${NC}"
    fi
else
    echo -e "Aidbox:     ${RED}not running${NC}"
fi

echo ""
echo "🔍 Available Updates (from Docker Hub):"
echo "--------------------------------------------------------"

# Check HAPI latest version
echo "Checking HAPI FHIR updates..."
HAPI_LATEST=$(curl -s "https://hub.docker.com/v2/repositories/hapiproject/hapi/tags?page_size=10" 2>/dev/null | grep -o '"name":"v[0-9.]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
if [ "$HAPI_LATEST" != "unknown" ]; then
    if [ "$HAPI_LATEST" == "$HAPI_PINNED" ]; then
        echo -e "HAPI FHIR:  ${GREEN}✓ Up to date ($HAPI_LATEST)${NC}"
    else
        echo -e "HAPI FHIR:  ${YELLOW}⚠ Update available: $HAPI_PINNED → $HAPI_LATEST${NC}"
    fi
else
    echo -e "HAPI FHIR:  ${RED}Could not check for updates${NC}"
fi

# Check Aidbox latest version
echo "Checking Aidbox updates..."
AIDBOX_LATEST=$(curl -s "https://hub.docker.com/v2/repositories/healthsamurai/aidboxone/tags?page_size=10" 2>/dev/null | grep -o '"name":"[0-9.]*"' | head -1 | cut -d'"' -f4 || echo "unknown")
if [ "$AIDBOX_LATEST" != "unknown" ] && [ "$AIDBOX_LATEST" != "latest" ]; then
    if [ "$AIDBOX_LATEST" == "$AIDBOX_PINNED" ]; then
        echo -e "Aidbox:     ${GREEN}✓ Up to date ($AIDBOX_LATEST)${NC}"
    else
        echo -e "Aidbox:     ${YELLOW}⚠ Update available: $AIDBOX_PINNED → $AIDBOX_LATEST${NC}"
    fi
else
    echo -e "Aidbox:     ${RED}Could not check for updates${NC}"
fi

echo ""
echo "📦 Local Docker Images:"
echo "--------------------------------------------------------"
docker images | grep -E "(REPOSITORY|hapi|aidbox)" | head -6

echo ""
echo "💡 To update a server:"
echo "  1. Review release notes"
echo "  2. Pull new version: docker pull hapiproject/hapi:v8.5.0"
echo "  3. Update docker-compose file"
echo "  4. Test: docker-compose -f docker-compose.test.yml up -d && cd api && pytest tests/"
echo "  5. Update FHIR_SERVER_VERSIONS.md"
echo ""
echo "📚 References:"
echo "  - HAPI releases: https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases"
echo "  - Aidbox releases: https://docs.aidbox.app/overview/release-notes"
echo "=================================================="
