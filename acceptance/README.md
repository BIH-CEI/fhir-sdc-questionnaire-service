# Acceptance battery

Checks a **deployed** Form Manager through its mTLS proxy, the same way a site
uses it. Run it after every deployment and hand the JUnit report to the
operator as the acceptance record.

    scripts/acceptance-test.sh https://formmanager.example.org site.pem site.key [server-ca.pem]

Needs Python 3.9+ (a virtualenv with pytest and httpx is created on first use)
and `openssl` (for the "untrusted CA" check). Writes `acceptance-report.xml`.

| Battery | Checks |
|---------|--------|
| 1 transport | TLS 1.2+, TLS 1.1 refused, server certificate valid for the host |
| 2 access | no certificate 401, untrusted CA 401, not allowlisted 403, allowlisted 200, nothing outside `/fhir/` |
| 3 readonly | writes 405; system operations, patient data, `$populate`/`$extract`/`$compute-and-extract`, Swagger 403. Every probe is harmless even if a rule were broken. |
| 4 content | MII PRO current and retained versions, PRO Library incl. release manifest, PCOR-MII, terminology installed |
| 5 operations | `$expand` (GET/POST), CRMI `$package` with outcome manifest first, `$languages`, `$localize`, errors as OperationOutcome |
| 6 latency | p95 of typical reads below `FM_LATENCY_P95` (default 2 s) |

Optional settings (environment):

| Variable | Purpose |
|----------|---------|
| `FM_SERVER_CA` | CA bundle for the server certificate (default: system trust store) |
| `FM_UNLISTED_CERT` / `FM_UNLISTED_KEY` | a trusted but not allowlisted certificate; enables the 403 checks |
| `FM_EXPECT_MII_PRO_VERSION`, `FM_EXPECT_MII_PRO_RETAINED`, `FM_EXPECT_PRO_LIBRARY_VERSION`, `FM_EXPECT_PCOR_MII_VERSION` | expected versions; default: this repository checkout, so run the suite from the tag that was deployed. Empty value skips the check. |
| `FM_LATENCY_P95`, `FM_LATENCY_SAMPLES`, `FM_EXPAND_SETTLE` | thresholds and waits |
| `ACCEPTANCE_ARGS` | extra pytest arguments, e.g. `-m "not latency"` |

CI runs the battery against the deployment bundle with the TEST-ONLY PKI on
every pull request (`scripts/test-deploy-bundle.sh`).
