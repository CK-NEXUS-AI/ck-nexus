# CK-NEXUS SelfCapability / AI-Team Reconciliation

Status: **Post-P0 development only**. This work is not production-closure evidence and cannot change Q10/Q11/Q12 or Production NO-GO.

## Goal

Promote the reported local SelfCapabilityManager, AI Team, Universal System, MCP server, launcher, and dedicated tests into canonical GitHub source with reproducible evidence.

## Required imported paths

The reconciliation gate fails closed until these exact paths exist:

- `creator_app/core/self_capability_manager.py`
- `creator_app/ai_team/universal_system.py`
- `creator_app/agnes/mcp_server.py`
- `start_all.sh`
- `run_anyclaw.py`

Dedicated tests must also exist in at least one of these locations:

- `tests/test_team.py`
- `tests/test_universal.py`
- `creator_app/ai_team/tests/test_*.py`

## Import rules

1. Import source code only; do not import `.env`, API keys, OAuth tokens, passwords, auth caches, or generated credential files.
2. Do not rewrite the reported local implementation from memory and call it imported evidence. Preserve the actual source when available.
3. Use the repository lockfile and `uv sync --all-extras --dev --frozen`. Do not use ad-hoc `pip install` as canonical dependency evidence.
4. The launcher must be fail-closed: if required tests, security checks, or server validation fail, it must not continue to advertise the runtime as ready.
5. OpenAPI and MCP are different integration surfaces. A FastAPI `/openapi.json` endpoint does not by itself prove an MCP server is available.
6. A ChatGPT-connected MCP surface must use an authenticated remote MCP boundary. Localhost-only services are not considered connected from ChatGPT until tool discovery succeeds from the ChatGPT side.
7. Reuse the canonical governed bridges where appropriate instead of exposing raw local execution ports publicly.

## CI acceptance

`.github/workflows/self-capability-reconciliation-ci.yml` requires:

- frozen dependency sync
- Python compile
- Ruff
- Bandit
- repository secret scan
- exact required-path handoff verification with SHA-256 evidence
- dedicated SelfCapability/AI-Team tests

The workflow intentionally fails while the reported local files are missing. A red result at this stage is a truthful blocker, not a regression in production closure.

## Completion criteria

Reconciliation is complete only when:

1. the actual source is committed on this Post-P0 branch;
2. the dedicated CI run is green;
3. the exact branch/commit and file SHA-256 values are recorded;
4. the MCP endpoint can be inspected as MCP and lists the expected tools;
5. ChatGPT discovers the authenticated remote MCP tools and can perform a read-only health call;
6. no production gate is promoted by this development evidence.
