# CK-NEXUS — Iron Rules for Automatic Tool Discovery and Execution

Status: project-level operating rules; apply to all future CK-NEXUS work.
Last updated: 2026-10-26

## Mission
Complete the user's primary task end-to-end as quickly as safely possible. Discover and reuse the best available tools automatically; coordinate Windows VPS, Linux VPS, Termux, MCP, GitHub, n8n, and AI workers as separate systems. Do not stop for repetitive confirmation or ask the user to repeat facts already available.

## 1. Automatic tool discovery and readiness
- At the start of a task, inspect the actual connected devices, installed commands, project tool/skill registries, dependency manifests, MCP servers, and relevant existing documentation.
- Prefer tools already installed, authenticated, and verified. Discover capabilities from authoritative registries/catalogues and official vendor sources where needed.
- Automatically prepare or install a missing, task-relevant tool when it is a bounded, reversible, non-destructive developer dependency, its source is trusted, compatibility is checked, and disk/network impact is acceptable.
- Before downloading/installing, check OS/architecture, version compatibility, package source/signature or checksum where available, disk space, network cost, licensing, and whether an equivalent tool already exists.
- Pin versions or use lockfiles where practical. Record the source, version, install command, verification command, and rollback/uninstall method in evidence.
- Do not install every tool indiscriminately. Install the smallest useful set for the current task; avoid duplicate frameworks and overlapping agents.
- If a tool is unavailable, unsafe, incompatible, unauthenticated, or blocked by permissions, continue with the best verified alternative and report the specific blocker only if it affects the primary outcome.

## 2. No-repeat-question execution
- Use the available context, connected apps, files, remote devices, and existing configuration to resolve routine details yourself.
- Do not ask the user to approve ordinary read-only inspection, diagnostics, safe tests, or bounded reversible local setup that fits these rules.
- Ask at most one concise question only when an essential decision cannot be safely inferred and the answer materially changes the outcome. Otherwise choose the safest reasonable default and continue.
- Never claim that a tool is installed, authenticated, available, or working until a real check proves it.

## 3. Multi-system control architecture
- Keep separate controllers and state/evidence for each target: Windows VPS, Linux VPS, Termux/Android, GitHub, n8n, and each MCP/AI runtime.
- Route tasks through the orchestrator; use AI reasoning for planning and diagnosis; use target-specific controllers for actions; use a policy gate for authority; use an evidence/verification loop to confirm outcomes.
- Run independent read-only checks and independent tasks in parallel. Bound concurrency, enforce task ownership/locks for conflicting writes, use timeouts and bounded retries with backoff, and cancel only work known to be safe to cancel.
- Never infer that a command succeeded on one device because another device succeeded. Record target identity, command, exit status, timestamps, and relevant redacted output.

## 4. Preserve work and stability
- Inspect Git status, diffs, untracked files, backups, service state, resource limits, and target paths before changes.
- Preserve every pre-existing tracked or untracked change. Never reset, clean, overwrite, delete, rotate credentials, or rebuild state stores merely to simplify a task.
- Make small, scoped, reversible changes. Back up a file before editing when its existing content may be affected. Prefer additive changes when feasible.
- Estimate disk/RAM/network impact before large installs, builds, image pulls, cache operations, or database migrations. Avoid resource-heavy work when the target is under pressure.
- Do not restart/reboot healthy services unnecessarily. If a component fails, isolate and recover only that component when safe.

## 5. Security and permission boundaries
- Automatically perform routine diagnostics, local tests, linting, secret scans, and non-destructive setup within existing granted authority.
- Never print, commit, upload, or include API keys, tokens, cookies, private keys, or credential-bearing config in logs/evidence.
- Do not expose loopback-only services publicly, weaken authentication/policy/sandbox boundaries, or bypass MCP/OMNI/Council/approval controls for speed.
- Do not silently perform irreversible/destructive actions, production deployments, public exposure, external messages, Git pushes/merges/releases, permission escalation, credential rotation, paid API activation, or material billing actions. Prepare and validate these steps automatically, then pause only at the actual consequential boundary for the required authorization.
- Treat downloaded code and skills as untrusted until source and behavior are reviewed. Do not execute arbitrary remote install scripts without inspecting them first.

## 6. Verification is mandatory
- Verify every meaningful action with the strongest practical check: exit code, test, health/status probe, file read-back, screenshot, API response, or end-to-end transaction.
- After edits, run focused tests first, then broader relevant tests; run git diff --check and security/secret checks where appropriate.
- For GUI control, capture the real target screen, confirm the intended window/device, perform a bounded action, then capture and inspect the resulting screen. If input is unreliable, report it as unverified rather than retrying blindly.
- Use explicit statuses: PASS, FAIL, BLOCKED, NOT VERIFIED, IN PROGRESS. A successful process start is not proof that the workflow completed.
- Never fabricate percentages, completion, test results, installation state, or evidence.

## 7. Evidence and continuity
- Store concise, sanitized evidence and update PROJECT_STATUS.md plus the relevant design/operations documentation when project state materially changes.
- Record what changed, why, files touched, commands/checks and their real outcomes, remaining blockers, rollback method, and next highest-priority action.
- Prefer existing project components and registries over installing new frameworks. Use the established control plane, policy gate, sandbox, test/security gates, and evidence exporter.
- Prioritize finishing the user's primary deliverable before optional enhancements. Avoid repetitive audits once valid, matching evidence exists; rerun only when state changed, evidence expired, or a new risk requires it.

## 8. Definition of done
A task is complete only when the primary outcome is delivered, relevant tests/checks pass, target-specific behavior is verified, no material regression is observed, evidence is recorded, and any remaining limitation is stated plainly. If blocked, finish all safe independent work and report the exact blocker plus the next actionable step.

## Windows VPS control priority (2026-10-26)
- Treat the Windows VPS as a first-class controlled target, not merely a secondary device. Keep a dedicated Windows controller and target-specific evidence separate from Linux VPS and Termux state.
- Prefer PowerShell-native, non-interactive diagnostics and command execution for speed/repeatability; use GUI control only when the task requires an actual desktop interaction.
- For every GUI action, require the loop: capture screenshot → identify target/window → perform one bounded action → capture screenshot again → verify the visible result. If mouse/keyboard input cannot be proven, report NOT VERIFIED and fall back to a safe CLI path where possible.
- Before installing tools, check PATH, package manager availability, disk space, current processes and existing project paths. Do not install Git/Python until source, version, scope, disk/resource impact, and installation method are established; no duplicate install attempts.
- Use one active writer per target/project; parallelize read-only diagnostics only. Keep timeouts short, capture exit codes/output, and verify state after each change.
- Current read-only check: Windows Server 2022 Standard online; Node/npm found; Git/Python/py/winget/choco not found through current PowerShell PATH/command lookup; C: has 81.4 GB free of 99.9 GB. This does not prove tools are absent outside PATH. No installation or configuration change performed.
