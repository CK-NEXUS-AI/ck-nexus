# CK-NEXUS Agent Operating Model

Status: proposed implementation. Activation depends on merging the pull request to the default branch and on the target agent harness supporting repository customizations.

## Purpose

Provide reusable specialist roles and skills for GitHub Copilot-compatible agent environments. These profiles do not create new runtime processes, grant external permissions, provide API credits, or independently authorize production actions. They define role-specific instructions and tool scopes for supported agent harnesses.

## Integration with the existing CK-NEXUS runtime

The repository already contains a separate in-process team in creator_app/ai_team/
(Director, Engineer, Guardian, Analyst, Researcher, Designer, and Connector), plus a
control-plane graph with research, implementation, verification, and security roles.
Its MCP inventory surfaces include cknexus_autonomy_status, cknexus_dev_assistants,
cknexus_dev_execution_plan, and cknexus_auto_dispatch.

These are distinct layers:

- The existing CK-NEXUS runtime roles are internal application behavior.
- The .github/agents/*.agent.md files are GitHub Copilot custom-agent profiles.
- The .github/skills/*/SKILL.md files are reusable task procedures.
- A profile file does not itself start a worker, authenticate a provider, or grant tools.
- Use cknexus_autonomy_status for inventory first; it is read-only and must not be
  interpreted as proof that an inference provider is authenticated or healthy.
- cknexus_dev_execution_plan is plan-only. Do not treat a planned task as executed.
- cknexus_auto_dispatch may invoke the in-process team; use it only for bounded
  development planning/work and retain the existing approval and evidence gates.

## Specialist roles

| Role profile | Default tool scope | Responsibility |
| --- | --- | --- |
| CK-NEXUS Coordinator | Read, search, agent delegation | Decompose work, coordinate reviewers, maintain status/evidence ledger |
| CK-NEXUS Planner | Read, search | Plan changes without editing |
| CK-NEXUS Implementer | Read, search, edit, execute | Make narrow changes, add tests, commit/push to intended branch |
| CK-NEXUS Security Reviewer | Read, search | Independent read-only adversarial review |
| CK-NEXUS Test Verifier | Read, search, execute | Reproduce and verify changes |
| CK-NEXUS Evidence Steward | Read, search | Validate evidence completeness, provenance, and subject identity |
| CK-NEXUS SRE Recovery | Read, search, execute | Diagnose SSH, Termux, and service recovery paths |

The available tools vary by host. A profile's tool list cannot grant a capability that the active host or account does not provide.

## Operating loop

1. **Discover:** inspect repository state, issue/PR, available tools, and current permissions.
2. **Plan:** define task scope, acceptance criteria, rollback, and exact target commit.
3. **Implement:** isolate changes on a feature branch and add regression tests.
4. **Review:** have a separate read-only security reviewer challenge the diff.
5. **Verify:** run focused checks and CI against the exact pushed commit.
6. **Evidence:** preserve logs, hashes, scan reports, and limitations.
7. **Report:** distinguish designed, implemented, executed, verified, and production.
8. **Learn:** update the relevant skill only when a reusable lesson is supported by evidence and reviewed.

## Non-negotiable governance

- CK-NEXUS Core/L3 remains the only canonical authority for state, memory, permissions, policy, execution, and evidence.
- AI agents, external tools, CI, and plugins have authority_level=NONE.
- No evidence means no completion claim. A green test does not certify Q10 or production.
- Q10/Q11/Q12 gates must not be silently weakened, bypassed, or relabeled.
- Preserve frozen subjects and canonical evidence. Never fabricate attestations, reviewer identity, scan IDs, or PASS states.
- No secret values in logs, prompts, commits, or reports.
- No paid compute/API usage without cost confirmation.
- No automatic merge or production deployment by virtue of agent approval.
- The Owner retains final authority; the Coordinator is advisory.

## Skills

- q10-evidence-integrity: canonical evidence and gate discipline.
- github-actions-triage: exact-commit CI debugging.
- secure-change-delivery: isolated changes, tests, review, and verified push.
- termux-rescue: safe SSH reverse-tunnel diagnosis and resilience checks.
- cknexus-tool-discovery: inspect available tools and avoid false credential/capability assumptions.

## Adoption and validation

Before merging, validate frontmatter and tool scopes, review the security boundary, and ensure required checks pass. After merge, verify the profiles appear in a supported agent picker and test one read-only task per role. Repository files alone do not prove the agents are activated or that independent subagent delegation is available.
