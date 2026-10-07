# CK-NEXUS n8n Development Super-Agent Fabric

Development-only automation layer for CK-NEXUS. It is intentionally separated from the production-closure subject and must not be used to promote Q10/Q11/Q12.

## v2 architecture

The v2 workflow is a two-pass council, not a single prompt fan-out.

Candidate generation roles:
- Orchestrator — mission decomposition, recovery planning, consolidation.
- Researcher — public research and standards mapping.
- Architect — architecture, API contracts, threat boundaries.
- Builder — development-only code/test proposals.
- Test Engineer — test design, failure analysis and regression planning.
- Performance Engineer — cost, latency and runtime performance analysis.
- UX Runtime Reviewer — runtime/UI integration and operator clarity.

Independent review roles:
- Verifier — independent tests and claim validation.
- Security Reviewer — secrets, injection, privilege, dependencies and trust boundaries.
- Evidence Auditor — evidence completeness, provenance and truth-label validation.

The final workflow state can reach `VERIFIED_DEVELOPMENT_CANDIDATE` only. It cannot emit Production Ready, Q10/Q11/Q12 PASS, merge authority or deployment authority.

## Skills and evaluation

`skill-registry.json` maps roles to approved development skills and explicitly forbids production deployment, production merge, protected-ref mutation, secret exfiltration, Q10 self-promotion and production-evidence rewrite.

`evaluation-policy.json` requires policy compliance, tests/test plan, security review, explicit evidence state, truth labels, no secrets and no production mutation. Hard-fail conditions override score-based evaluation.

## Authority boundary

CK-NEXUS Governor remains authoritative for state, permissions, policy and execution. n8n coordinates work but cannot self-approve production mutation. `main`, `release/q10-q16-closure`, PR #14, merge, production deploy, production tags, raw-secret access and Q10 promotion without native Codex Security evidence are denied.

## Runtime contract

Legacy workflow: `POST /webhook/ck-nexus/dev-agent`.

Super-Agent v2 workflow: `POST /webhook/ck-nexus/super-agent`.

Both call `CK_NEXUS_AGENT_ENDPOINT`, which should normally point to a local CK-NEXUS sidecar endpoint `/v1/agent`.

Sidecar v1 binds to `127.0.0.1:8765` by default. AGNES Sidecar v2 may run on the development-isolated port `127.0.0.1:8776`. Both validate branch/role/authority flags before forwarding specialist work. If `CK_NEXUS_INTELLIGENCE_ENDPOINT` is not configured, the sidecar returns `PROPOSAL_ONLY` instead of fabricating an executed result.

Optional runtime variables:
- `CK_NEXUS_AGENT_ENDPOINT=http://127.0.0.1:8765/v1/agent`
- `CK_NEXUS_INTELLIGENCE_ENDPOINT=<CK-NEXUS development intelligence endpoint>`
- `CK_NEXUS_INTELLIGENCE_TOKEN=<ephemeral brokered development token>`
- `CK_NEXUS_TOOL_ENDPOINT=http://127.0.0.1:8766/v1/tool`
- `CK_NEXUS_TOOL_TOKEN=<ephemeral brokered development token>`

No API key or token is stored in this repository or workflow.

## Groq development intelligence

`ck_nexus_groq_dev_adapter.mjs` is the source-controlled Groq development adapter. It binds to localhost, uses `GROQ_API_KEY` only from the runtime environment, defaults to `openai/gpt-oss-120b`, returns sanitized upstream failure metadata, and hard-labels all results as non-production.

On Windows, `start_agnes_groq_dev_stack.ps1` starts the governed AGNES development stack:

- Tool Gateway: `127.0.0.1:8766`
- Groq development adapter: `127.0.0.1:8767`
- AGNES Sidecar v2: `127.0.0.1:8776`

The launcher reads the Groq credential from a DPAPI-protected file (default `C:\CK-N8N\secure\groq-api-key.dpapi`) under the current Windows user, generates ephemeral internal tool/intelligence tokens, removes the decrypted key from the parent environment after the adapter starts, performs health checks, and writes non-secret startup evidence to `C:\CK-N8N\evidence\agnes-groq-runtime-startup-latest.json`.

For scheduled startup, run the launcher under the same Windows user that created the DPAPI credential. Do not copy the encrypted credential to another user profile and assume it will decrypt.

## Evidence states

A model-generated `verdict: PASS` is not independent verification. Runtime execution should remain `EXECUTED_UNVERIFIED` / `UNVERIFIED_UNTIL_INDEPENDENT_CHECK` until exact source identity, tests, tool-path behavior, security review and evidence provenance are independently checked.

`VERIFIED_DEVELOPMENT_CANDIDATE` is the maximum development promotion. It is not Production Ready and cannot alter Q10/Q11/Q12 state.

## Windows development install

Use `install_n8n_windows.ps1`. The installer pins n8n 2.35.7 and binds n8n to `127.0.0.1:5678`. `start_n8n_dev.ps1` starts the local development instance.

The Windows instance is for development automation only. Q12 still requires the dedicated non-root delegated-cgroup-v2 Linux verifier environment.

Before activation, run `n8n audit` and review credentials, database, filesystem, risky nodes and instance findings. Keep the instance local-only until the audit and webhook smoke tests pass.

## Production safety

This fabric must never be interpreted as Q10/Q11/Q12 evidence. Q10 requires the native Codex Security Deep Security Scan; Q11 and Q12 must use their authoritative exact-subject verifier workflows after Q10 passes.
