# CK-NEXUS AGNES Master Upgrade — Skill Nervous System

Status: **R13-LAB Development Candidate / RC / NO-GO**
Baseline: R9–R11 canonical implementation commit `d917f810f822f16f57adb776edba55bea875da98`
History rule: **append-only / no protected-history rewrite / no silent knowledge deletion**

## 1. Consolidated system intent

CK-NEXUS is being extended from a governed multi-agent platform into a governed AI operating system. The earlier image-derived blueprint contributed API gateway, system design discipline, agentic workflows, idea expansion, content/business systems, AI tool categories, model/provider abstraction, runtime and retrieval abstraction, coding governance, decision intelligence, security boundaries, automation control, and business operating modes.

AGNES is the next development layer: a skill-driven nervous system that lets an AI agent discover and activate reusable procedures and tools without handing raw user credentials to the model. Skills are portable instructions and capability contracts. They are not billing credentials and they do not bypass provider authentication.

## 2. Non-negotiable invariants

1. Preserve all prior source history, evidence, knowledge, and release identity.
2. Upgrades happen on new branches/workspaces. No force push, history rewrite, or silent overwrite of protected evidence.
3. Learning is append-only. New knowledge may supersede old knowledge through explicit links/status, but historical records remain available.
4. AGNES does not receive raw user API keys and cannot bulk-export credentials.
5. Local/offline model execution is preferred for the no-user-key path.
6. Cloud execution, when intentionally enabled, must use brokered service/account authorization outside the agent context.
7. Skills are discovered as metadata first. Unknown/community executable code is quarantined before activation.
8. External writes, permission changes, purchases, destructive operations, production mutation, merge, and deployment remain approval-gated.
9. All important actions carry correlation ID, execution ID, skill ID/version, policy version, evidence identity, and outcome.
10. R12 staging evidence remains mandatory before any production-ready claim.

## 3. AGNES body / nervous-system map

| Body analogy | CK-NEXUS component | Purpose |
|---|---|---|
| Brain | Planner + source verifier + provider router | Analyze, route, plan, verify |
| Eyes | Web/news/model/file/image skills | Observe public/current/project information |
| Ears | Audio/event listener adapters | Receive speech/events |
| Mouth | Report/explain/draft output | Communicate verified results |
| Hands | Code patch/test/security scan/artifact tools | Perform bounded workspace work |
| Legs | Workspace Broker + controlled terminal | Move work into isolated local/external workspaces |
| Nervous system | Orchestration + tracing + approvals + state machine | Coordinate skills and execution |
| Memory | Append-only knowledge/evidence ledger | Retain learning without erasing history |
| Immune system | Guardrails + secret policy + skill quarantine + rollback | Prevent unsafe or unverified actions |

## 4. One canonical skill file

`creator_app/skills/agnes/SKILL.md` is the single canonical skill manifest for AGNES. It contains global invariants and a machine-readable manifest block. The runtime loads this file, validates unique skill IDs, and activates only the skills relevant to the current goal.

Initial skill set:

- `brain.plan`
- `brain.verify_sources`
- `eyes.web_research`
- `eyes.model_watch_50`
- `eyes.file_read`
- `eyes.image_understand`
- `ears.transcribe`
- `memory.append_knowledge`
- `nerves.trace`
- `immune.policy_check`
- `immune.skill_quarantine`
- `hands.code_patch`
- `hands.test`
- `hands.security_scan`
- `legs.workspace_open`
- `legs.git_branch`
- `mouth.report`
- `upgrade.self_improve`

## 5. No-user-key execution strategy

A skill gives AGNES procedural knowledge. It cannot replace inference compute or a provider's authentication requirement. The correct architecture is:

```text
Goal
  -> Skill Registry
  -> Skill Plan
  -> Provider/Tool capability request
  -> Policy check
  -> Local runtime if available
       Ollama / future vLLM / approved local model
     else
       BLOCKED unless a service-managed/brokered account path is explicitly enabled
  -> Tool/Workspace execution
  -> Evidence
```

User API keys are therefore not an AGNES input. They are neither copied into prompts nor exposed as tool results. The current R13-LAB AGNES path reports itself blocked if there is no local/mock runtime rather than silently falling back to a user OpenAI key.

## 6. Skills and tool ecosystem discovered for integration

### Agent Skills format

Use portable `SKILL.md` metadata/instructions as the skill packaging format. Discovery may read name/description first, then activate full instructions only when relevant. Bundled scripts are never trusted solely because a skill manifest exists.

### MCP

Use MCP as the standard tool/data connector plane. Keep its primitives separate:

- Tools: executable capabilities.
- Resources: application-controlled context/data.
- Prompts: reusable user-controlled templates.

MCP server discovery does not imply activation. Each server/tool is translated into the CK-NEXUS Capability Registry and receives risk, permission, credential, network, timeout, idempotency, and approval metadata before use.

### OpenAI Agents SDK

Keep it as one supported agent runtime behind CK-NEXUS policy. Useful capabilities include function tools, agents-as-tools/handoffs, guardrails, sessions, tracing, sandbox agents, shell/apply-patch tooling, and human-in-the-loop. CK-NEXUS remains the owner of the outer policy, approval, credential, audit, and production gates.

### Agnes open-source runtime

AGNES can optionally interoperate with the external/open-source agnes runtime through MCP/ACP/CLI/API adapters. The external runtime is not allowed to become the source of truth for CK-NEXUS permissions or credentials.

### External workspaces

Workspace Broker currently models four providers:

1. Local isolated workspace — default development path.
2. E2B — isolated external Linux coding sandbox candidate.
3. GitHub Codespaces — repository-bound external development workspace candidate.
4. Daytona — optional external sandbox candidate.

External workspaces remain disabled-by-default until a service/account authorization is configured behind the broker and the action is approved.

## 7. Skill discovery and quarantine pipeline

```text
Discovery source
  -> Fetch metadata only
  -> Capture canonical source URL/repository identity
  -> Capture version/tag/commit
  -> Capture license
  -> Capture checksum/signature where available
  -> Enumerate scripts/assets/references
  -> Enumerate requested tools
  -> Enumerate network egress
  -> Enumerate credential scopes
  -> Static review
  -> Security scan
  -> Quarantine verdict
  -> Isolated smoke test
  -> Capability contract generation
  -> Human/Council review when risk is material
  -> Activate versioned skill
```

Automatic discovery is allowed. Blind automatic installation/execution is not.

## 8. Model Watch 50

The model-watch skill is a bounded research pipeline, not an auto-upgrade switch.

```text
Collect newest model metadata (max 50)
  -> Deduplicate provider/model/version aliases
  -> Resolve canonical provider identity
  -> Verify release claims against primary provider documentation
  -> Record modality/context/tool support/local-vs-cloud/pricing-or-quota metadata
  -> Check CK-NEXUS compatibility and policy
  -> Queue isolated benchmark/eval
  -> Compare against current routed models
  -> Produce adoption proposal
  -> Council review
  -> Approval for routing change
  -> Append verified registry record
```

A new model is never automatically promoted to production routing merely because it appears in a catalog.

## 9. Full governed self-upgrade lifecycle

The lifecycle below is the canonical automation sequence. Safe local development may run continuously through the review package; merge/canary/external/high-impact actions stop at the approval boundary.

1. **Trigger** — schedule, user request, model/news watch, dependency alert, failed gate, or idea proposal.
2. **Acquire baseline identity** — branch, commit, tag, artifact hash, environment identity.
3. **Discover** — identify candidate skill/tool/model/framework/data source.
4. **Capture provenance** — source owner, URL/repository, version/commit, date, license, checksum/signature.
5. **Quarantine** — executable or unknown candidates remain inactive.
6. **Verify source** — use primary/official documentation when current technical claims matter.
7. **Extract capability** — convert marketing/library language into a normalized capability contract.
8. **Compare with current system** — present/partial/missing/conflict/redundant.
9. **Risk classification** — read-only, local-write, external-write, high-impact.
10. **Permission analysis** — required role, tool permission, network egress, credential scope, filesystem scope.
11. **Architecture check** — layer ownership, interface, state, failure behavior, idempotency, retry, circuit, audit, rollback.
12. **Upgrade proposal** — expected value, changed files/components, migration impact, acceptance criteria, non-goals.
13. **Council review** — Architect, Research, Product/UX, Builder, Security/QA/DevOps perspectives as relevant.
14. **Create isolated workspace** — exact baseline; no production filesystem mutation.
15. **Create feature branch** — never rewrite protected history.
16. **Expose task-scoped skills only** — least tool surface and no credential export.
17. **Implement bounded change** — files outside allowlist remain untouched.
18. **Compile/static validation** — syntax/schema/import validation.
19. **Targeted tests** — new behavior, negative behavior, permissions, failure paths.
20. **Regression tests** — existing non-billing and relevant integration tests.
21. **Security checks** — secret scan, SAST, dependency/audit checks when tools exist, network/redirect/SSRF policy.
22. **Evals/benchmark** — quality, tool correctness, cost/resource use, latency, model/provider compatibility.
23. **Failure injection** — timeout, provider failure, workspace failure, invalid skill, unavailable credential, corrupt ledger.
24. **Evidence build** — machine-readable PASS/FAIL/BLOCKED records tied to commit/artifact/environment.
25. **Diff review** — changed files, API/DB/config impacts, migration, backward compatibility.
26. **Rollback plan** — exact rollback/ref/recovery steps before promotion.
27. **Approval checkpoint** — required for merge, external writes, canary, production, destructive/high-impact action.
28. **Merge candidate** — only after approval and branch protection checks.
29. **Canary** — bounded users/traffic/environment.
30. **Observe** — health, metrics, logs, traces, cost, tool error rate, policy violations.
31. **Automatic rollback** — if SLO/gate/policy threshold is violated.
32. **Post-canary verification** — compare expected vs actual behavior.
33. **Learning record** — append verified findings, evidence links, limitations, and supersession links.
34. **Model/skill registry update** — version/status changes are append-oriented; old records remain traceable.
35. **Production gate compiler** — only R12-equivalent required evidence can change the final release posture.

## 10. Failure rules

- No local model: AGNES inference is BLOCKED unless an explicitly permitted service-managed provider is enabled.
- Skill source unknown: QUARANTINED.
- Checksum/license missing: QUARANTINED.
- Skill asks for credentials/network/scripts: additional review; no blind activation.
- Ledger integrity failure: STOP learning writes and raise integrity incident.
- Production mutation request: BLOCKED by default.
- External workspace without authorization: BLOCKED.
- Approval service unavailable: approval-required action remains BLOCKED.
- Test/security scan unavailable: record BLOCKED, not PASS.
- New model without primary verification/eval: CANDIDATE only.
- Canary fails: ROLLBACK.

## 11. Current implementation evidence

R13-LAB targeted AGNES tests: 13 PASS.
R8–R13 non-billing regression: 131 PASS.
Full suite in this sandbox: 137 PASS / 3 billing setup errors caused by missing `aiosqlite`.
The full production evidence sprint is still not complete.

## 12. Next implementation slices

1. R12 staging evidence closure remains highest priority.
2. Add live local-model AGNES runner using the existing Ollama provider adapter.
3. Add MCP client adapter with per-tool capability contracts and quarantine activation flow.
4. Add real Workspace Broker adapters one at a time, starting with local sandbox and then GitHub Codespaces/E2B when service authorization is available.
5. Add Model Watch 50 collectors with primary-source verification and append-only registry persistence.
6. Add evaluation harness for skill selection, tool authorization, source verification, coding task quality, and regression protection.
7. Add Control Tower UI for skills, executions, approvals, workspaces, model candidates, evidence, and ledger integrity.

## 13. Definition of AGNES self-development

AGNES is considered self-developing only when it can autonomously discover, research, propose, branch, implement, test, scan, evaluate, produce evidence, and learn **inside bounded development environments**. It is not authorized to silently mutate production, bypass approval, spend money, create credentials, weaken controls, or erase prior knowledge.
