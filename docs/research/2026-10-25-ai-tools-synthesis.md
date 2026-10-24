# CK-NEXUS AI Tooling Research — Final Synthesis
Research date: 2026-10-25. Ratings are analyst judgments based on source verifiability, operational maturity and available evidence—not certification or endorsement.

## A. Comparison table

| Tool | Level | Autonomy | Evidence strength | Cost | Self-host | Maturity 1–5 |
|---|---|---|---|---|---|---:|
| GitHub Copilot | 1 | Assistant → task agent | High features/pricing; task-specific productivity study | Free; paid plans | No full product | 5 |
| Cursor | 1 | Assistant → task agent | High features/pricing; limited independent comparisons | Free; paid + model usage | No full product | 5 |
| Aider | 1 | Git-aware assistant | High source/features; limited comparative benchmarks | OSS + inference | Client yes | 4 |
| Cline | 1 | Interactive task agent | High source/features; limited independent benchmarks | OSS + inference; optional paid provider | Client yes | 4 |
| Claude Code | 2 | Task agent/subagents | High docs; model/harness dependent | Subscription/API | Client local; inference hosted | 5 |
| OpenAI Codex CLI | 2 | Task agent/subagents | High docs; benchmark configuration matters | OSS client + model/compute cost | CLI yes | 5 |
| Devin | 2 | Managed task agent | Medium; vendor docs/integrations | Paid usage; verify quote | No | 4 |
| OpenHands | 2 | Task agent/SDK | High architecture/pricing; scores version-dependent | Free OSS + model/compute | Yes | 4 |
| Hive | 3 | Repo-maintenance multi-agent | Medium architecture; requested metrics unverified | OSS + model/compute | Yes | 3 |
| Captain Claw | 3 | Multi-agent/proactive loop | Medium; many claims project-reported | OSS + model/compute | Yes | 3 |
| OpenHands Control Plane | 3 | Multi-agent governance | High feature descriptions; limited outcome evidence | Enterprise custom | VPC option | 4 |
| Kitchen Loop | 4 | Continuous self-optimization | Medium; public paper, author-reported results | Paper reports ~$0.38/PR; not universal | Implementation-dependent | 3 |
| SkillCode (skc) | 4 | Claimed self-evolution | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| Jeffy Loop | 4 | Recursive audit/fix loop | Medium-low; public repo, broad metrics unverified | Model cost applies | Local hook yes | 2 |
| BPS Agent Framework | 4 | Claimed self-improvement/tool creation | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| Qodo | 5 | Review/governance | High features/pricing; limited independent outcomes | Trial; paid team/enterprise | Enterprise option | 4 |
| Constraints Registry | 5 | Policy-as-code/MCP validation | High repo design; limited adoption evidence | OSS + validator/ops costs | Yes | 3 |
| LazyKeel | 5 | Claimed deterministic supervisor | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| FailGate | 5 | Claimed test-lock/acceptance layer | Low for named product; stronger evidence for ImpossibleBench | No public evidence for product | Unknown | 1 |

Evidence strength reflects source verifiability; maturity reflects availability and inspectability, not intelligence.

## B. Decision tree by team archetype

- **Solo developer:** Start with Aider or Cline for provider flexibility; try Copilot Free or Cursor Hobby for low-friction editor workflows. If a supported ChatGPT plan is already available, evaluate Codex CLI before buying another subscription. Pick one primary agent.
- **Small team:** Use Copilot/Cursor for daily editing and one bounded task agent (Claude Code, Codex CLI or OpenHands) behind PR review. Standardize tests, secret scanning and branch protection.
- **Mid-size org:** Evaluate Copilot governance, OpenHands Control Plane or Qodo where RBAC, SSO, audit, budget and cross-repo rules matter. Add Constraints Registry for deterministic policy, but enforce hard rules in CI.
- **Research lab:** Use OpenHands or Codex CLI/SDK with held-out tasks and immutable oracles.

## C. Top five red flags for production multi-agent systems

1. **Votes without independence:** multiple roles share the same underlying model/account, unavailable agents count as votes, or no quorum is recorded.
2. **Mutable acceptance oracle:** the coding agent can edit tests, fixtures, success criteria, benchmark data or the judge approving its own patch.
3. **Excessive credentials/network:** agents inherit production secrets, unrestricted egress or broad GitHub/Gmail/Drive permissions.
4. **No stop/budget controls:** no deadline, iteration cap, spend ceiling, queue backpressure, cancellation or human escalation.
5. **Evidence without provenance:** a “pass” is not tied to exact commit SHA, pinned dependencies and complete logs; skipped tests silently count as success.

## D. Top five recommendations for 2026

1. **Extend CK-NEXUS's existing Council and Capability Authority.** The repository already has debate, provider routing, research and authority components. Connect them rather than install a competing runtime. Keep advisory consensus separate from signed execution grants.
2. **Use Codex CLI or Claude Code as isolated workers.** Both offer useful task-agent workflows and subagents. Run in per-task worktrees/containers with least privilege and independent tests; neither agent should approve its own patch.
3. **Adopt Constraints Registry patterns for policy-as-code.** Its versioned constraints and OPA/Conftest/Checkov/Semgrep adapters are inspectable and low-cost. Since guidance retrieval can fail open, hard policies must also fail closed in CI.
4. **Lock acceptance tests before self-evolution.** ImpossibleBench research shows how agents may exploit contradictory or mutable tests. Hash baseline tests, protect fixtures, prohibit self-approval and fail on altered/skipped tests.
5. **Pilot one supervisor, then measure.** Hive suits repository maintenance; OpenHands Control Plane suits enterprise governance; Qodo suits code review/context; Captain Claw is a broader self-hosted fleet reference. Pilot one option and measure accepted PRs, regressions, reviewer time and cost before adopting overlapping control planes.

## E. Evidence gaps

- **Identity gaps:** SkillCode (`skillcode_optimize_self`, “23+ super skills”, Auto-Forge), BPS Agent Framework, LazyKeel and the named FailGate product could not be uniquely identified in authoritative primary sources. Claims remain **No public evidence** until a canonical repository and reproducible test are supplied.
- **Hive:** ACMM levels and the repo-maintenance architecture are documented; “six types of suffering,” 74 CI/CD workflows, 32 nightly suites and bug-to-fix under 30 minutes were not independently corroborated.
- **Jeffy Loop:** public source and receipts exist, but 132 projects / 103 converged / 56 merged PRs and corporate attributions were not verified.
- **Kitchen Loop:** 285+ iterations, 1,094+ merged PRs, zero detected regressions and ~$0.38/PR are paper-reported results. “Zero detected” is not zero actual defects.
- **ImpossibleBench:** the 76% GPT-5 result applies to a particular impossible-task split and scaffold. A later audit reports control-task/scoring issues; this is not a universal cheating rate.
- **Commercial tools:** official docs are useful for features/pricing but not independent performance rankings. Copilot's 55.8% productivity finding is task-specific, not a 2026 Copilot-vs-Cursor trial. Qodo's review claims need independent precision/recall evaluation.
- **Control planes:** RBAC, budgets, SSO and audit features should be verified with negative tests. A policy dashboard does not prove enforcement.

## CK-NEXUS disposition

Recommended baseline: **existing Development Council + real provider health/quota checks + signed Capability Authority + isolated worker worktrees + immutable acceptance tests + independent verification + audit trail**. Prefer free/open-source clients where practical, but account separately for inference and compute. Do not add another control plane until a measured gap remains. External Gmail/file writes should be opt-in, scoped and audited; do not grant agents blanket permanent-deletion authority. Keep VPS cleanup evidence-driven and preserve runtime state, secrets and existing Git changes.
