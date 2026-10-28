# CK-NEXUS Mandatory Team Workflow

## Status

Approved design; implementation begins with the bounded Auto Developer prompt contract. This document does not claim that separate live agents are available unless provider/session evidence proves it.

## Rule

Every development, investigation, and research task must pass through the same named work stages. A task may not skip a stage because it appears easy. For tiny changes, a role may be completed in a short record, but the record must remain visible.

## Required roles and outputs

1. **Researcher** — inspect repository state, existing implementation, tests, official/primary sources as relevant; label facts, assumptions, unknowns, and citations.
2. **Architect** — define the smallest safe change, interface boundaries, affected paths, acceptance criteria, dependencies, and rollback/stop conditions.
3. **Implementer** — make only the scoped change in an isolated worktree; preserve pre-existing changes and never modify protected paths outside explicit authorization.
4. **Independent Reviewer** — inspect the diff against the task and acceptance criteria; check regressions, security, scope creep, and missing failure cases.
5. **Test and Evidence Owner** — run focused tests first, then relevant integration/regression checks; capture exact commands, exit codes, summaries, source SHA/tree, and artifact references.
6. **Synthesis Lead** — reconcile disagreement, list unresolved risks, distinguish verified findings from recommendations, and report what remains blocked.

Each role must produce: `role`, `assigned_question`, `findings`, `evidence_refs`, `assumptions`, `risks`, and `recommendation`.

## Council independence and voting

- Never represent role-play inside one model as independent agents or independent votes.
- Count a voter as independent only when its live provider/model identity and successful response are evidenced; unavailable, timed-out, or quota-blocked providers are excluded from the eligible-voter denominator.
- If fewer than three independent live voting units respond, label the outcome `INSUFFICIENT_QUORUM`; do not claim majority authorization.
- For eligible low-risk proposals, approval requires more than 50% of eligible participating independent voters to support the same proposal, with evidence and dissent recorded.
- Duplicate accounts, aliases, or multiple personas backed by the same model/provider do not increase the independent-voter count.
- If the live Council is unavailable, proceed only with work permitted by the existing single-agent execution policy; mark the result `SINGLE_AGENT_MULTI_PERSPECTIVE`, not Council-approved.

## Authority and safety boundary

Council votes can recommend or authorize only within capabilities explicitly granted by the Policy Kernel / Capability Authority. Votes cannot self-grant permissions, alter the policy that governs the same task, expose credentials, disable tests, approve their own evidence, or bypass security/path/secret scanning. Credential changes, destructive data operations, access-control changes, firewall/network exposure, production deployment, and merge to `main` remain separately gated and human-reviewed unless a separately verified policy explicitly authorizes a narrower action.

## Required execution sequence

`Intent -> Research -> Architecture/Acceptance Criteria -> Council Review/Vote (when independent live voters exist) -> Capability/Policy Check -> Isolated Worktree -> Implement -> Independent Review -> Tests/Scans -> Evidence Record -> Learning -> Eligible Branch Publication`

Research and implementation are distinct. A report, benchmark claim, or recommendation must not be treated as implementation evidence. Local test success is not live or production verification.

## Research reports

For tool evaluations, assign tools to separate research work packets while preserving the requested order in the final synthesis. Prefer primary sources: official documentation, official repositories, peer-reviewed papers, benchmark owners, and dated case studies. Every numerical or material product claim needs an inline source. Use `No public evidence` where no suitable source is found and state the closest verifiable proxy when sources conflict.

## Acceptance criteria

- Auto Developer prompts always include the required roles and their output schema.
- Prompts explicitly prohibit fake independent-voter claims and prohibit Council votes from bypassing existing authority gates.
- Focused tests verify the prompt contract.
- Existing user changes and production-readiness gates remain intact.
- Any claim that multiple agents actually participated must be backed by distinct live session/provider evidence, not just the prompt text.
