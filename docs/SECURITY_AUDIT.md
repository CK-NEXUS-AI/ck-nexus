# Security Audit — v0.2.0

Audit date: 2026-08-05  
Scope: `creator_app/`, `services/`, `main.py`, web assets, dependency environment, and delivery files.

## Verified checks

| Check | Result | Evidence |
|---|---|---|
| Plaintext secret pattern scan | PASS | No OpenAI/Stripe/private-key pattern found outside ignored local/runtime paths |
| Python compilation | PASS | `compileall` exit 0 |
| Automated tests | PASS | 26 passed |
| Static lint | PASS | Ruff: no findings |
| Python security scan | PASS | Bandit: exit 0, no reported finding |
| Installed dependency audit | PASS | `pip-audit`: no known vulnerabilities found on 2026-08-05 |
| Frontend JavaScript syntax | PASS | `node --check creator_app/web/app.js` |
| Installed wheel smoke | PASS | Installed artifact, console entry point, health, catalog, and Demo run |

`pip-audit` results reflect the installed locked environment and public advisory data available at scan time. A passing result is not proof that no vulnerability exists.

## Security controls present

- OpenAI credentials are server-side environment values and are not returned by the status endpoint.
- Optional CK-NEXUS bearer protection uses constant-time comparison.
- Request bodies, prompt length, session identifiers, history limits, runtime duration, and generation rate are bounded.
- API/provider errors are translated to stable messages without echoing a key.
- CSP, frame denial, MIME sniffing denial, referrer restriction, and browser permissions restrictions are set.
- No permissive CORS policy is enabled.
- Model output and API-derived strings are rendered with DOM `textContent`.
- Browser access tokens are held in session storage, not persistent local storage.
- The Docker container runs as a non-root application user.
- The default server binding is loopback-only.
- OpenCode execution is isolated to a dedicated Git worktree, uses normal permission checks, and requires deterministic post-run verification.
- Commercial-license placeholders and third-party license approval require seller/legal input.
- Test the release archive on each operating system promised to buyers.

### P1 — before public internet exposure

- The access token is a single shared secret, not multi-user identity. Put the app behind HTTPS and a maintained identity-aware proxy for remote use.
- Rate limiting is process-local and resets on restart; it is not suitable for horizontally scaled public deployment.
- SQLite and local Agents SDK sessions are intended for one application worker and an individual creator.
- Add centralized logs, alerting, backup/restore rehearsal, and host-level patch management.

### P2 — post-MVP hardening

- Add end-to-end browser tests across supported browsers.
- Add SBOM generation and license-policy automation.
- Add remote database, distributed rate limiting, queue isolation, and role-based authorization before a multi-user SaaS edition.

## Assessment

The checked source is suitable as a **Sellable MVP Candidate** for local-first individual use. The
Development execution endpoints are suitable only for a trusted operator and must not be exposed as a public
general-purpose coding service. The product must not be represented as fully production-complete
or enterprise-ready until the P0 gates above are closed.
