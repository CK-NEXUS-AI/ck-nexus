# CK-NEXUS AI Tooling Research — Final Synthesis
Research date: 2026-10-25. Scope: the 19 tools requested by the project owner. Ratings below are analyst judgments from public primary-source verifiability, product maturity signals and the evidence collected—not certification or endorsement.

## A. Comparison table

| Tool | Level | Autonomy | Evidence strength | Cost | Self-host | Maturity 1–5 |
|---|---|---|---|---|---|---:|
| GitHub Copilot | 1 | Assistant → task agent | High for product/pricing; medium for productivity generalization | Free tier; paid individual/org plans | No full product | 5 |
| Cursor | 1 | Assistant → task agent | High for features/pricing; limited independent comparative evidence | Free tier; paid plans + model usage | No full product | 5 |
| Aider | 1 | Assistant with Git-aware edits | High for source/features; limited comparative benchmark | OSS + inference cost | Client yes | 4 |
| Cline | 1 | Interactive task agent | High for source/features; limited independent benchmark | OSS + provider usage; optional hosted plans | Client yes | 4 |
| Claude Code | 2 | Task agent; subagents | High for docs; benchmark depends on exact model/harness | Subscription or API/provider billing | Client/runtime local; model generally hosted | 5 |
| OpenAI Codex CLI | 2 | Task agent; subagents | High for architecture/docs; benchmarks need exact config | OSS client; subscription/API and optional sandbox cost | CLI yes; managed harness varies | 5 |
| Devin | 2 | Managed task agent | Medium: vendor docs and integrations; limited independent verification | Paid usage/plan; exact quote verify | No | 4 |
| OpenHands | 2 | Task agent/SDK; orchestration | High for open architecture and pricing; benchmark version-dependent | Free OSS + model/compute; enterprise custom | Yes | 4 |
| Hive | 3 | Repo-maintenance multi-agent; ACMM policy | Medium for architecture; specified numeric claims unverified | OSS/runtime + model cost; hosted terms verify | Yes | 3 |
| Captain Claw | 3 | Multi-agent + proactive loop | Medium for code/features; claims largely project-reported | OSS + provider/compute cost | Yes | 3 |
| OpenHands Agent Control Plane | 3 | Multi-agent governance | High for published feature description; limited independent outcome evidence | Enterprise custom | VPC/self-host enterprise option | 4 |
| Kitchen Loop | 4 | Continuous self-optimization | Medium: public paper, author-reported production metrics | Reported ~$0.38/PR in paper; not universal | Implementation-dependent | 3 |
| SkillCode (skc) | 4 | Claimed self-evolution | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| Jeffy Loop | 4 | Recursive audit/fix loop | Medium-low: public repo and demonstrations; broad metrics unverified | Loop may be free; model cost applies | Local hook yes | 2 |
| BPS Agent Framework | 4 | Claimed self-improvement/tool creation | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| Qodo | 5 | Review/governance layer | High for product/pricing; limited independent outcome proof | Trial; Pro Team and enterprise paid | Enterprise on-prem option | 4 |
| Constraints Registry | 5 | Policy-as-code/MCP validation | High for repository design; independent adoption evidence limited | OSS + validators/ops | Yes | 3 |
| LazyKeel | 5 | Claimed deterministic supervisor | Very low; canonical source not identified | No public evidence | No public evidence | 1 |
| FailGate | 5 | Claimed acceptance/test-lock layer | Low for named product; stronger evidence for related ImpossibleBench research | No public evidence for FailGate; benchmark OSS | Product unknown | 1 |

**Evidence-strength rubric:** High = identifiable official docs/repository plus testable details; Medium = primary-source feature evidence but limited independent evaluation; Low = incomplete independent replication or mostly vendor/project claims; Very low = no uniquely identifiable primary source for the named product. Maturity measures operational availability and inspectability, not intelligence.

## B. Decision tree by team archetype

1. **Solo developer:** Start with Aider or Cline if model choice and cost control matter; use Copilot Free or Cursor Hobby to test the workflow without committing to a subscription. If already using an OpenAI subscription and terminal workflow, evaluate Codex CLI. Choose one primary editor/agent first, not four overlapping agents.
2. **Small team:** Use Copilot or Cursor for daily coding and add a single bounded task agent (Claude Code, Codex CLI or OpenHands) behind PR review. Standardize repository instructions, branch protection, secret scanning and a test command. OpenHands is attractive when self-hosting and provider flexibility outweigh operations burden.
3. **Mid-size organization:** Start with an existing GitHub/Copilot governance path or evaluate OpenHands Control Plane/Qodo where RBAC, SSO, audit, budgets and cross-repo rules are needed. Add Constraints Registry for deterministic constraints only after making required validators fail closed in CI. Do not jump to autonomous auto-merge until the codebase has reliable independent tests and measurable escape rates.
4. **Research lab:** Use OpenHands, Codex CLI/SDK or custom harnesses for reproducibility, controlled sandboxing and model comparisons. Kitchen Loop and Jeffy Loop are useful research patterns, but preserve held-out tasks, immutable acceptance oracles and per-run artifacts. Treat unverified SkillCode/BPS/LazyKeel/FailGate names as source-verification tasks, not dependencies.

## C. Top five red flags before production multi-agent adoption

1. **Votes without independence:** multiple roles use the same model/account, unavailable agents count as votes, or no quorum is recorded.
2. **Mutable acceptance oracle:** the implementation agent can alter tests, fixtures, benchmark data, success criteria or the judge that approves its patch.
3. **Excessive credentials/network:** agents inherit production secrets, unrestricted egress, broad GitHub tokens or mail/file access unrelated to the task.
4. **No budget/stop controls:** no iteration cap, deadline, spend ceiling, queue backpressure, cancellation or human escalation path.
5. **Evidence without provenance:** “passed” is not tied to an exact commit SHA, pinned dependency versions, complete test logs and an independent verifier; skipped tests are silently counted as success.

## D. Top five recommendations for 2026

1. **Build on CK-NEXUS's existing Council and Capability Authority.** The repository already contains debate, provider routing, research and authority components. Connecting them avoids a second competing runtime. Keep advisory consensus separate from execution grants.
2. **Use Codex CLI or Claude Code as isolated workers, not final approvers.** Both provide useful task-agent workflows and subagents; run them in per-task worktrees/containers with least privilege and a deterministic test suite.
3. **Adopt Constraints Registry patterns for policy-as-code.** Its versioned constraints and OPA/Conftest/Checkov/Semgrep integrations are inspectable and low-cost. Critical policies must be enforced in CI, because a queryable MCP registry alone is not enforcement.
4. **Add test-locking and an independent regression oracle before self-evolution.** ImpossibleBench research demonstrates that agents can exploit contradictory or mutable tests. Preserve immutable acceptance tests, hash test artifacts, prohibit self-approval, and fail closed on altered/skipped tests.
5. **Pilot one supervisor and measure accepted changes.** Hive is a candidate for repo maintenance; OpenHands Control Plane for enterprise governance; Qodo for review/context; Captain Claw for broader self-hosted fleet ideas. Select one based on a 2–4 week pilot measuring accepted PRs, escaped regressions, review time, cost per accepted change and operational burden. Do not adopt multiple overlapping control planes at once.

## E. Evidence gaps and unresolved claims

- **High-priority identity gaps:** SkillCode (`skillcode_optimize_self`, 23+ skills, Auto-Forge), BPS Agent Framework, LazyKeel and the named FailGate product could not be uniquely identified from authoritative primary sources. Mark every product-specific claim `No public evidence` until a canonical repository, license, pinned version and reproducible test are supplied.
- **Hive:** the repository verifies ACMM levels and the co-maintainer architecture, but the requested “six types of suffering,” 74 CI/CD workflows, 32 nightly suites and bug-to-fix under 30 minutes were not independently corroborated.
- **Jeffy Loop:** public source and receipts are discoverable; the requested 132 projects / 103 converged / 56 merged PRs and company attributions were not verified in this pass.
- **Kitchen Loop:** 285+ iterations, 1,094+ merged PRs, zero detected regressions and ~$0.38/PR are paper-reported results. “Zero detected” is not the same as zero real regressions, and independent replication remains important.
- **ImpossibleBench / FailGate:** the 76% GPT-5 result refers to a specific impossible-task split and scaffold. A later public audit reports issues in control tasks/scoring, so the figure must be cited with methodological caveats; it is not a universal rate of cheating in production.
- **Commercial coding tools:** official docs reliably describe features and current pricing, but not necessarily comparative outcomes. The Copilot 55.8% productivity result is task-specific and not a 2026 Copilot-vs-Cursor benchmark. Qodo review claims need independent precision/recall evaluation.
- **Control planes:** RBAC, budgets, SSO and audit-log feature lists should be verified with negative tests. A UI showing a policy does not prove the runtime enforces it.

## CK-NEXUS disposition

Recommended baseline: **existing Development Council + provider health/quota checks + signed Capability Authority + isolated worker worktrees + immutable acceptance tests + independent verification + audit trail**. Use free/open-source clients where practical, but budget model inference and VPS compute separately. Do not add a new full control plane until a specific measured gap remains. Keep external Gmail/file write actions opt-in, scoped and audited; do not grant blanket permanent deletion authority to agents. Keep the current VPS's working files, secrets, runtime state and Git changes intact while cleanup is evidence-driven.
