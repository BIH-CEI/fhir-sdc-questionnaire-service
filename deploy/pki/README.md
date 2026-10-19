# Operator PKI (not in git)

Put these four files here (or point `PKI_DIR` elsewhere):

| File | Content |
|------|---------|
| `ca.pem` | Bundle of CAs whose client certificates are accepted |
| `server.pem`, `server.key` | Server certificate and key for the proxy's hostname |
| `allowlist.map` | One line per allowed site: `<sha1-fingerprint> <site>;` |

Fingerprint of a client certificate, in the format nginx compares:

    openssl x509 -in site.pem -noout -fingerprint -sha1 | cut -d= -f2 | tr -d : | tr 'A-F' 'a-f'

`*.pem` and `*.key` are git-ignored. With `MTLS_ENV=production` the proxy refuses
to start with the TEST-ONLY PKI from `deploy/mtls/test-pki/`.
