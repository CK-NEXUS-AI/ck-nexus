# Test Report — v0.2.0

Execution date: 2026-08-05

## Automated result

- Python test suite: **26 passed**
- Ruff: **PASS**
- Bandit: **PASS**
- Dependency audit: **PASS — no known vulnerabilities found**
- JavaScript syntax: **PASS**
- Secret scan: **PASS**
- Python compile: **PASS**
- Wheel package/entry point and Demo API smoke: **PASS**
- Delivery ZIP internal/external SHA-256 verification and exclusion checks: **PASS**

## Covered behavior

- Health/status response and security headers
- Four-agent catalog and typography control-hub delivery
- Demo generation and SQLite history persistence
- Stable unknown-agent/provider errors
- Safe failure when Live Mode lacks a key
- Optional bearer authorization
- Generation rate limiting and body-size limits
- Session-ID validation and session deletion
- Configuration validation and storage behavior
- Existing optional billing-module tests
- OpenCode Auto Developer worktree isolation, normal permission checks, and deterministic post-run verification

## Manual/blocked validation

- Live OpenAI request: **BLOCKED — no usable API key available in this build session**
- Live OpenCode model response: **NOT VERIFIED — CLI availability does not prove provider entitlement or successful inference**
- Clean network install on buyer target OS: **PENDING**
- Cross-browser visual regression: **PENDING**
- Docker image build/run: **BLOCKED — Docker CLI unavailable in this environment**
- Seller terms and final commercial license: **PENDING SELLER INPUT**
