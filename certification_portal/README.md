# CK-NEXUS Certification Portal prototype

**Status: local read-only assessment demo; NOT deployed publicly; NOT a certification issuer.**

Run from the repository root with the isolated Python 3.12 environment:

```bash
/tmp/cknexus-install-venv-py312-approved-20261117/bin/uvicorn certification_portal.app:app --host 127.0.0.1 --port 18765
```

Routes:
- `GET /` — local dashboard and owner-signoff preview form.
- `GET /health` — demo health.
- `POST /api/assess/local` — fixed, read-only checks against this local checkout only.
- `POST /api/owner-signoff-preview` — demo-only Ed25519 declaration preview.

The assessment never accepts a URL, shell command, repository path, or credential from the requester. It runs a fixed set of local checks with a timeout. Dirty worktree and an unadopted V2 policy deliberately force `NOT_CERTIFIED`. No certificate is issued.

The owner form is a UI/API prototype only. Its key is ephemeral and regenerated each process start; no identity authentication, legal signature, persistent audit record, or durable trust is provided. Do not treat its signature as a legal or production signature.

Before production use: authenticated identity, CSRF protection, durable managed signing keys/KMS, immutable evidence storage, versioned policy/profile registry, isolated assessment workers, genuinely independent verifier, revocation/expiry, PDF/QR, audit retention, tenant isolation, threat model, penetration test, and explicit production approval are still required.
