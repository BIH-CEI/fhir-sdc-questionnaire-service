#!/bin/bash
#
# Repository Split Migration Script
# Splits fhir-sdc-questionnaire-service into two repositories:
# - fhir-sdc-api (core SDC implementation)
# - fhir-workshop-demo (workshop materials)
#
# Run from: /Users/thome/code/interop-prototypes/fhir-sdc-questionnaire-service
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
SOURCE_DIR="$SCRIPT_DIR"

API_REPO="$PARENT_DIR/fhir-sdc-api"
WORKSHOP_REPO="$PARENT_DIR/fhir-workshop-demo"

echo "========================================"
echo "Repository Split Migration"
echo "========================================"
echo ""
echo "Source:   $SOURCE_DIR"
echo "API repo: $API_REPO"
echo "Workshop: $WORKSHOP_REPO"
echo ""

# Check if target directories already exist
if [ -d "$API_REPO" ] || [ -d "$WORKSHOP_REPO" ]; then
    echo "ERROR: Target directories already exist!"
    echo "Please remove them first:"
    echo "  rm -rf $API_REPO"
    echo "  rm -rf $WORKSHOP_REPO"
    exit 1
fi

echo "Creating target directories..."
mkdir -p "$API_REPO"
mkdir -p "$WORKSHOP_REPO"

# ============================================
# FHIR-SDC-API Repository
# ============================================
echo ""
echo "========================================"
echo "Creating fhir-sdc-api..."
echo "========================================"

# Core directories
echo "Copying api/..."
cp -r "$SOURCE_DIR/api" "$API_REPO/"

echo "Copying hapi-config/..."
cp -r "$SOURCE_DIR/hapi-config" "$API_REPO/"

echo "Copying hapi-scripts/..."
cp -r "$SOURCE_DIR/hapi-scripts" "$API_REPO/"

echo "Copying scripts/..."
cp -r "$SOURCE_DIR/scripts" "$API_REPO/"

# GitHub workflows
if [ -d "$SOURCE_DIR/.github" ]; then
    echo "Copying .github/..."
    cp -r "$SOURCE_DIR/.github" "$API_REPO/"
fi

# Docker files
echo "Copying docker-compose files..."
cp "$SOURCE_DIR/docker-compose.yml" "$API_REPO/"
cp "$SOURCE_DIR/docker-compose.test.yml" "$API_REPO/"
cp "$SOURCE_DIR/docker-compose.aidbox.yml" "$API_REPO/"

# Environment
if [ -f "$SOURCE_DIR/.env" ]; then
    cp "$SOURCE_DIR/.env" "$API_REPO/.env.example"
fi
cp "$SOURCE_DIR/.gitignore" "$API_REPO/"

# README (use new one)
cp "$SOURCE_DIR/migration/fhir-sdc-api-README.md" "$API_REPO/README.md"

# Documentation
echo "Copying documentation..."
for doc in ARCHITECTURE.md REQUIREMENTS.md SDC_FORM_MANAGER_REQUIREMENTS.md \
           FORM_MANAGER_CAPABILITIES.md TEST_REQUIREMENTS_MAPPING.md TESTING.md \
           TESTING_ACCOMPLISHMENTS.md MULTI_SERVER_TESTING.md SDC_CONFIGURATION.md \
           FHIR_VALIDATOR_INTEGRATION.md FHIR_SERVER_VERSIONS.md VERSION_QUICK_REFERENCE.md \
           VERSION_IN_METADATA_EXPLAINED.md IMPLEMENTING_ASSEMBLE_OPERATION.md \
           ASSEMBLE_OPERATION_SUMMARY.md PRODUCTION_STATUS.md KNOWN_LIMITATIONS.md \
           REFERENCE_IMPLEMENTATION_PLAN.md; do
    if [ -f "$SOURCE_DIR/$doc" ]; then
        cp "$SOURCE_DIR/$doc" "$API_REPO/"
    fi
done

# Initialize git
echo "Initializing git repository..."
cd "$API_REPO"
git init
git add .
git commit -m "Initial commit: Split from fhir-sdc-questionnaire-service

This repository contains the core SDC API implementation:
- FastAPI service with \$package and \$localize operations
- HAPI FHIR configuration
- Test infrastructure
- Documentation

Split from: fhir-sdc-questionnaire-service"

echo "fhir-sdc-api created successfully!"

# ============================================
# FHIR-WORKSHOP-DEMO Repository
# ============================================
echo ""
echo "========================================"
echo "Creating fhir-workshop-demo..."
echo "========================================"

# Core directories
echo "Copying demo-ui/..."
cp -r "$SOURCE_DIR/demo-ui" "$WORKSHOP_REPO/"

echo "Copying terminology-proxy/..."
cp -r "$SOURCE_DIR/terminology-proxy" "$WORKSHOP_REPO/"

echo "Copying workshop-config/..."
cp -r "$SOURCE_DIR/workshop-config" "$WORKSHOP_REPO/"

echo "Copying workshop-scripts/..."
cp -r "$SOURCE_DIR/workshop-scripts" "$WORKSHOP_REPO/"

echo "Copying workshop-scenarios/..."
cp -r "$SOURCE_DIR/workshop-scenarios" "$WORKSHOP_REPO/"

# Docker file (renamed)
echo "Copying docker-compose.workshop.yml as docker-compose.yml..."
cp "$SOURCE_DIR/docker-compose.workshop.yml" "$WORKSHOP_REPO/docker-compose.yml"

# Git config
cp "$SOURCE_DIR/.gitignore" "$WORKSHOP_REPO/"

# README (use new one)
cp "$SOURCE_DIR/migration/fhir-workshop-demo-README.md" "$WORKSHOP_REPO/README.md"

# Documentation
echo "Copying workshop documentation..."
if [ -f "$SOURCE_DIR/WORKSHOP_ARCHITECTURE.md" ]; then
    cp "$SOURCE_DIR/WORKSHOP_ARCHITECTURE.md" "$WORKSHOP_REPO/ARCHITECTURE.md"
fi

# Initialize git
echo "Initializing git repository..."
cd "$WORKSHOP_REPO"
git init
git add .
git commit -m "Initial commit: Split from fhir-sdc-questionnaire-service

This repository contains the workshop demonstration materials:
- Demo UI for interactive scenarios
- Terminology proxy with LOINC enhancements
- Multi-site HAPI FHIR configuration
- Sample questionnaires and scenarios

Split from: fhir-sdc-questionnaire-service"

echo "fhir-workshop-demo created successfully!"

# ============================================
# Summary
# ============================================
echo ""
echo "========================================"
echo "Migration Complete!"
echo "========================================"
echo ""
echo "Created repositories:"
echo "  - $API_REPO"
echo "  - $WORKSHOP_REPO"
echo ""
echo "Next steps:"
echo ""
echo "1. Test fhir-sdc-api:"
echo "   cd $API_REPO"
echo "   docker compose up -d"
echo "   cd api && pytest tests/ -v"
echo ""
echo "2. Test fhir-workshop-demo:"
echo "   cd $WORKSHOP_REPO"
echo "   docker compose up -d"
echo "   open http://localhost:8100"
echo ""
echo "3. Create GitHub repositories and push:"
echo "   cd $API_REPO && git remote add origin <url> && git push -u origin main"
echo "   cd $WORKSHOP_REPO && git remote add origin <url> && git push -u origin main"
echo ""
echo "4. Archive or delete the original repository once verified."
