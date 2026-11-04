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

Both call `CK_NEXUS_AGENT_ENDPOINT`, which should normally point to the local CK-NEXUS n8n sidecar endpoint `/v1/agent`.

The sidecar binds to `127.0.0.1:8765` by default. It validates branch/role/authority flags before forwarding specialist work. If `CK_NEXUS_INTELLIGENCE_ENDPOINT` is not configured, it returns `PROPOSAL_ONLY` instead of fabricating an executed result.

Optional runtime variables:
- `CK_NEXUS_AGENT_ENDPOINT=http://127.0.0.1:8765/v1/agent`
- `CK_NEXUS_INTELLIGENCE_ENDPOINT=<CK-NEXUS development intelligence endpoint>`
- `CK_NEXUS_INTELLIGENCE_TOKEN=<brokered development token if required>`

No API key or token is stored in this repository or workflow.

## Windows development install

Use `install_n8n_windows.ps1`. The installer pins n8n 2.35.7 and binds n8n to `127.0.0.1:5678`. `start_n8n_dev.ps1` starts the local development instance.

The Windows instance is for development automation only. Q12 still requires the dedicated non-root delegated-cgroup-v2 Linux verifier environment.

Before activation, run `n8n audit` and review credentials, database, filesystem, risky nodes and instance findings. Keep the instance local-only until the audit and webhook smoke tests pass.

## Production safety

This fabric must never be interpreted as Q10/Q11/Q12 evidence. Q10 requires the native Codex Security Deep Security Scan; Q11 and Q12 must use their authoritative exact-subject verifier workflows after Q10 passes.
