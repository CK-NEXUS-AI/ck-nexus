# CK-NEXUS R16 Dependency & Security Baseline Validation

Baseline: R14 Cognitive Brain Runtime, commit `ca2a6379fd60401f84cd420322f1d1fd4d763865`, tag `v0.2.0-r14-cognitive-brain-dev.1`.

## Increment

- Added an offline dependency preflight that validates all direct runtime and verification extras without contacting a package registry.
- Expanded `requirements-dev.txt` to include `dev,billing,email,gateway,github-app` extras.
- Made dependency audit a required release check rather than an advisory warning.
- Kept production behavior fail-closed; no deployment automation was added.

## Verification in this environment

- Dependency preflight implementation tests: PASS (2/2).
- Non-billing regression: PASS (170/170).
- Full suite: BLOCKED/PARTIAL (176 passed, 3 setup errors; `aiosqlite` unavailable).
- Dependency preflight: BLOCKED (11/21 direct requirements satisfied; 10 unavailable/incompatible in host environment).
- Ruff: BLOCKED (module unavailable).
- Bandit: BLOCKED (module unavailable).
- pip-audit: BLOCKED (module unavailable).
- Secret scan: PASS (259 tracked files).
- Python compile: PASS.
- Clean `uv sync --all-extras --frozen`: BLOCKED because the package registry cannot be resolved from this execution environment.

## Production decision

**NO-GO.** This increment improves reproducibility and prevents security/dependency checks from being treated as optional, but it does not close the dependency/security production gate until a network-enabled or pre-provisioned clean environment can install the locked dependencies and execute Ruff, Bandit, pip-audit, and the full billing suite.
