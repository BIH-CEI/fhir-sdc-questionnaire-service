Access is machine-to-machine with **mutual TLS**. A site's system (typically its own FHIR server pulling content) presents a client certificate; browsers are not expected clients.

| Step | Rule | Result if not met |
|------|------|-------------------|
| 1. Authentication | The client certificate chains to a CA in the server's trust bundle | `401` OperationOutcome (`login`) |
| 2. Authorisation | The certificate's SHA-1 fingerprint is on the site allowlist | `403` OperationOutcome (`forbidden`) |
| 3. Routing | Only paths under `/fhir/` are served | `404` OperationOutcome (`not-found`) |

A valid certificate alone is not enough: CAs like DFN/GÉANT TCS issue certificates to many organisations, so every site is registered individually by fingerprint (as in the NUM Data Sharing Framework).

### Joining as a site

1. Obtain a client certificate from a CA the service trusts (for the pilot: as agreed with BIH-CEI).
2. Send the certificate (not the key) to the operators. They add its fingerprint to the allowlist:

       openssl x509 -in site.pem -noout -fingerprint -sha1

3. Call the service with certificate and key, e.g.

       curl --cert site.pem --key site.key https://<host>/fhir/metadata

For certificate rotation, register the new fingerprint before the old certificate expires; both stay valid until the old one is removed.

### Identity and audit

The proxy forwards the site identity to the backend (`X-Client-Site`, `X-Client-Cert-Fingerprint`, `X-Client-Cert-Subject`) and overwrites any client-supplied values. Every request is logged with site, fingerprint and path.

### Not yet implemented

- **Per-site licence gate:** today every allowlisted site sees all content. Licensed instruments (e.g. EORTC) will be restricted per site, based on a CRMI manifest per site.
- **Revocation checking** (CRL/OCSP).
