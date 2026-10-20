Every error response is a FHIR `OperationOutcome` (`application/fhir+json`), from the proxy, from HAPI and from the sidecar alike.

| HTTP status | `issue.code` | Typical cause |
|-------------|--------------|---------------|
| 400 | `invalid` | Wrong resource type, inconsistent request |
| 401 | `login` | No client certificate, or one from an untrusted CA (proxy) |
| 403 | `forbidden` | Certificate not on the allowlist, or a blocked path: system operation, patient-data type or operation (proxy) |
| 404 | `not-found` | Unknown resource, version or path |
| 405 | `not-supported` | Method not allowed; any write on this read-only service (proxy) |
| 409 | `conflict` | Version conflict |
| 422 | `processing`; `structure` / `invalid` for malformed requests | Request cannot be processed; malformed requests carry an `expression` pointing to the problem |
| 500 / 502 | `exception` | Server error or upstream failure (no internal details are returned) |

The human-readable message is in `issue.diagnostics`. See the [example](OperationOutcome-example-error.html).

`$package` reports **content** problems (e.g. a missing ValueSet) not as an error but as messages inside the package's outcome manifest; see [Operations](operations.html).
