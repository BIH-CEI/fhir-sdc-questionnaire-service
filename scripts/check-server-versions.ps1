# Check FHIR server versions and compare with available updates
# PowerShell version for Windows

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "FHIR Test Server Version Checker" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Current Pinned Versions
Write-Host "📋 Current Pinned Versions (from docker-compose files):" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------"

$hapiPinned = (Select-String -Path "docker-compose.test.yml" -Pattern "image:.*hapi:" | ForEach-Object { $_.Line -replace '.*hapi:', '' -replace '\s*#.*', '' }).Trim()
Write-Host "HAPI FHIR:  " -NoNewline
Write-Host $hapiPinned -ForegroundColor Green

$aidboxPinned = (Select-String -Path "docker-compose.aidbox.yml" -Pattern "image:.*aidboxone:" | ForEach-Object { $_.Line -replace '.*aidboxone:', '' -replace '\s*#.*', '' }).Trim()
Write-Host "Aidbox:     " -NoNewline
Write-Host $aidboxPinned -ForegroundColor Green

Write-Host ""
Write-Host "🏃 Running Versions (from containers):" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------"

# Check HAPI
$hapiRunning = docker ps --format '{{.Names}}' | Select-String -Pattern "hapi-fhir-test"
if ($hapiRunning) {
    try {
        $metadata = Invoke-RestMethod -Uri "http://localhost:8081/fhir/metadata" -TimeoutSec 5
        $version = $metadata.software.version
        Write-Host "HAPI FHIR:  " -NoNewline
        Write-Host "v$version (running)" -ForegroundColor Green
    } catch {
        Write-Host "HAPI FHIR:  " -NoNewline
        Write-Host "running but version unknown" -ForegroundColor Yellow
    }
} else {
    Write-Host "HAPI FHIR:  " -NoNewline
    Write-Host "not running" -ForegroundColor Red
}

# Check Aidbox
$aidboxRunning = docker ps --format '{{.Names}}' | Select-String -Pattern "aidbox-fhir-test"
if ($aidboxRunning) {
    try {
        $logs = docker logs aidbox-fhir-test 2>&1 | Select-String "Version:" | Select-Object -Last 1
        $version = ($logs -split " ")[2]
        Write-Host "Aidbox:     " -NoNewline
        Write-Host "$version (running)" -ForegroundColor Green
    } catch {
        Write-Host "Aidbox:     " -NoNewline
        Write-Host "running but version unknown" -ForegroundColor Yellow
    }
} else {
    Write-Host "Aidbox:     " -NoNewline
    Write-Host "not running" -ForegroundColor Red
}

Write-Host ""
Write-Host "📦 Local Docker Images:" -ForegroundColor Yellow
Write-Host "--------------------------------------------------------"
docker images | Select-String -Pattern "(REPOSITORY|hapi|aidbox)" | Select-Object -First 6

Write-Host ""
Write-Host "💡 To update a server:" -ForegroundColor Cyan
Write-Host "  1. Review release notes"
Write-Host "  2. Pull new version: docker pull hapiproject/hapi:v8.5.0"
Write-Host "  3. Update docker-compose file"
Write-Host "  4. Test: docker-compose -f docker-compose.test.yml up -d; cd api; pytest tests/"
Write-Host "  5. Update FHIR_SERVER_VERSIONS.md"
Write-Host ""
Write-Host "📚 References:" -ForegroundColor Cyan
Write-Host "  - HAPI releases: https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases"
Write-Host "  - Aidbox releases: https://docs.aidbox.app/overview/release-notes"
Write-Host "  - Version tracking: FHIR_SERVER_VERSIONS.md"
Write-Host "=================================================="
