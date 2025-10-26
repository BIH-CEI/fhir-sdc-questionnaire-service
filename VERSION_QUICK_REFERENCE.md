# FHIR Server Version Management - Quick Reference

## 📌 Current Setup (As of 2025-10-26)

| Server | Pinned Version | Why Pinned? |
|--------|----------------|-------------|
| **HAPI FHIR** | `v8.4.0` | ✅ Reproducible tests across team/CI |
| **Aidbox** | `2509.0` | ✅ Reproducible tests across team/CI |

**Status**: ✅ **Versions are now pinned!**

---

## ⚡ Quick Commands

### Check Current Versions

```bash
# See pinned versions in docker-compose
grep "image:" docker-compose.test.yml
grep "image:" docker-compose.aidbox.yml

# Check running HAPI version
curl -s http://localhost:8081/fhir/metadata | grep version

# Check running Aidbox version
docker logs aidbox-fhir-test | grep "Version:"

# Run version checker (if PowerShell enabled)
powershell -ExecutionPolicy Bypass -File scripts/check-server-versions.ps1

# Or use bash version
bash scripts/check-server-versions.sh
```

### Update to New Version

```bash
# Example: Update HAPI from v8.4.0 to v8.5.0

# 1. Check release notes
# https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases

# 2. Pull new image
docker pull hapiproject/hapi:v8.5.0

# 3. Backup current config
cp docker-compose.test.yml docker-compose.test.yml.backup

# 4. Edit docker-compose.test.yml
# Change: image: hapiproject/hapi:v8.4.0
# To:     image: hapiproject/hapi:v8.5.0

# 5. Restart and test
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d
cd api
pytest tests/ -v

# 6. If tests pass - update docs
# Edit FHIR_SERVER_VERSIONS.md
# Add entry to version history table

# 7. Commit changes
git add docker-compose.test.yml FHIR_SERVER_VERSIONS.md
git commit -m "Update HAPI FHIR: v8.4.0 → v8.5.0"
```

---

## 🔍 Why Version Pinning Matters

### ❌ Before (Using `:latest`)

```yaml
image: hapiproject/hapi:latest  # 😱 Version changes without notice
```

**Problems:**
- Tests pass Monday, fail Tuesday (server auto-updated)
- Different versions on dev/staging/CI
- Can't reproduce test failures
- Breaking changes appear randomly

### ✅ After (Pinned Versions)

```yaml
image: hapiproject/hapi:v8.4.0  # 🎯 Explicit, reproducible
```

**Benefits:**
- ✅ Same version everywhere (dev, CI, team)
- ✅ Controlled updates (you decide when)
- ✅ Reproducible test results
- ✅ Easy rollback if needed

---

## 🎯 Do External Servers Update?

### HAPI FHIR (Docker)
- **Updates**: Yes, new releases ~monthly
- **How**: Manual docker pull + docker-compose change
- **Your control**: 100% (pinned version)

### Aidbox (Docker)
- **Updates**: Yes, new releases frequently
- **How**: Manual docker pull + docker-compose change
- **Your control**: 100% (pinned version)

### Smile CDR (Public Server)
- **Updates**: Yes, vendor controlled
- **How**: Automatic (no notice)
- **Your control**: 0% (external service)
- **Mitigation**: Mark tests as `@pytest.mark.flaky`

### Future: Azure FHIR / AWS HealthLake
- **Updates**: Yes, Microsoft/AWS controlled
- **How**: Automatic rolling updates
- **Your control**: Limited (can pin API version)

---

## 📊 Version Update Frequency Recommendations

| Server | Check for Updates | Update Frequency | Priority |
|--------|-------------------|------------------|----------|
| **HAPI** | Monthly | Quarterly | Medium |
| **Aidbox** | Monthly | As needed | Low |
| **PostgreSQL** | Quarterly | Annually | Low |

---

## 🚨 When to Update Immediately

Update ASAP when:
- 🔴 Security vulnerability announced
- 🔴 Critical bug affecting your tests
- 🟡 SDC specification changes
- 🟡 FHIR version update needed

**Don't update when:**
- ❌ In middle of sprint
- ❌ Right before release
- ❌ Test suite is unstable

---

## 📝 Version Update Checklist

```markdown
- [ ] Review release notes
- [ ] Check breaking changes
- [ ] Pull new image locally
- [ ] Update docker-compose file
- [ ] Restart containers
- [ ] Run full test suite
- [ ] Check test coverage hasn't dropped
- [ ] Update FHIR_SERVER_VERSIONS.md
- [ ] Update VERSION_QUICK_REFERENCE.md (this file)
- [ ] Commit changes with descriptive message
- [ ] Notify team in Slack/Email
- [ ] Monitor CI/CD for 24 hours
```

---

## 🔧 Troubleshooting

### Tests fail after version update

```bash
# Rollback to previous version
git checkout docker-compose.test.yml
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d
cd api && pytest tests/ -v
```

### Multiple versions cached locally

```bash
# List all HAPI images
docker images | grep hapi

# Remove old versions (keep pinned!)
docker rmi hapiproject/hapi:latest
docker rmi hapiproject/hapi:v8.3.0

# Verify only pinned version remains
docker images | grep hapi
```

### Can't pull new version

```bash
# Clear Docker cache
docker system prune -a

# Pull with no-cache
docker pull hapiproject/hapi:v8.5.0 --no-cache
```

---

## 📚 Resources

| Resource | Link |
|----------|------|
| **HAPI Releases** | https://github.com/hapifhir/hapi-fhir-jpaserver-starter/releases |
| **Aidbox Releases** | https://docs.aidbox.app/overview/release-notes |
| **Version Tracker** | `FHIR_SERVER_VERSIONS.md` (this repo) |
| **Docker Hub - HAPI** | https://hub.docker.com/r/hapiproject/hapi/tags |
| **Docker Hub - Aidbox** | https://hub.docker.com/r/healthsamurai/aidboxone/tags |

---

## 🎓 Best Practices

1. **Pin versions** - Always use specific tags, never `:latest`
2. **Document changes** - Update `FHIR_SERVER_VERSIONS.md` after each update
3. **Test before committing** - Run full test suite before pushing version changes
4. **Communicate** - Notify team when updating versions
5. **Keep history** - Maintain version history in `FHIR_SERVER_VERSIONS.md`
6. **Review regularly** - Check for updates monthly, update quarterly

---

**Last Updated**: 2025-10-26
**Next Review**: 2026-01-26 (3 months)
