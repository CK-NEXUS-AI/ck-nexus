---
name: ck-nexus-agnes
version: 1.0.0
description: CK-NEXUS AGNES skill nervous system. Local-first, append-only, governed, and upgrade-oriented.
---

# CK-NEXUS AGNES — Unified Skill Nervous System

AGNES is the governed capability layer for CK-NEXUS. Skills describe *how* to perform work; they do not grant credentials or bypass provider billing. The runtime must prefer local inference and brokered service credentials. User API keys are not exposed to AGNES.

## Global invariants

1. Existing project history and knowledge are preserved. Upgrades append; they do not silently delete or replace prior evidence.
2. AGNES never receives raw user API keys. Credential access stays behind CK-NEXUS Credential Broker/provider adapters.
3. Local/offline execution is preferred when a capable local runtime exists.
4. External writes, production mutation, purchases, permission changes, and destructive operations require explicit approval through the execution controller.
5. Coding work occurs in an isolated workspace/branch, followed by compile, tests, security scan, evidence, review, and only then a merge/canary decision.
6. New skills are discovered as metadata first. Unknown/community skills remain quarantined until source, license, checksum, permissions, and tool surface are reviewed.
7. Learning is append-only: new facts supersede old facts by linkage/status, not by deleting historical records.
8. Every skill invocation must carry correlation, execution, skill version, policy version, and evidence metadata.

## Body map

- Brain: reasoning, planning, source verification, routing.
- Eyes: web/news/model discovery, file/document/image understanding.
- Ears: transcription/event listening adapters.
- Mouth: report/draft/explain outputs.
- Hands: patch code, run tests, scan security, create artifacts.
- Legs: open/enter isolated workspaces and controlled external terminals.
- Nervous system: event routing, tracing, approvals, state transitions.
- Memory: append-only knowledge/evidence ledger.
- Immune system: policy, secret safety, sandbox, supply-chain review, rollback.

<!-- CKNEXUS_SKILL_MANIFEST_BEGIN -->
```json
{
  "manifest_version": 1,
  "agent": "AGNES",
  "skills": [
    {"id":"brain.plan","version":"1.0.0","organ":"brain","description":"Break a goal into bounded, auditable steps.","capabilities":["planning","routing"],"risk":"read_only","approval_required":false,"executor":"internal","tags":["plan","design","roadmap","analyze"]},
    {"id":"brain.verify_sources","version":"1.0.0","organ":"brain","description":"Cross-check current claims against trusted and primary sources.","capabilities":["research","verification"],"risk":"read_only","approval_required":false,"executor":"research","tags":["verify","research","source","news","latest"]},
    {"id":"eyes.web_research","version":"1.0.0","organ":"eyes","description":"Read public web sources through an approved research connector.","capabilities":["web","research"],"risk":"read_only","approval_required":false,"executor":"mcp_or_hosted","tags":["web","search","news","docs"]},
    {"id":"eyes.model_watch_50","version":"1.0.0","organ":"eyes","description":"Discover up to 50 newly listed AI models, deduplicate them, and queue verification against primary sources.","capabilities":["model_discovery","research"],"risk":"read_only","approval_required":false,"executor":"research","tags":["model","latest","ai","watch","catalog"]},
    {"id":"eyes.file_read","version":"1.0.0","organ":"eyes","description":"Read approved project files without mutation.","capabilities":["filesystem_read"],"risk":"read_only","approval_required":false,"executor":"workspace","tags":["file","read","repo","document"]},
    {"id":"eyes.image_understand","version":"1.0.0","organ":"eyes","description":"Extract concepts and structured observations from images through an approved vision runtime.","capabilities":["vision","analysis"],"risk":"read_only","approval_required":false,"executor":"provider","tags":["image","scan","vision","diagram"]},
    {"id":"ears.transcribe","version":"1.0.0","organ":"ears","description":"Transcribe approved audio through a local or brokered speech adapter.","capabilities":["audio","transcription"],"risk":"read_only","approval_required":false,"executor":"provider","tags":["audio","voice","transcribe","listen"]},
    {"id":"memory.append_knowledge","version":"1.0.0","organ":"memory","description":"Append verified knowledge with provenance and supersession links; never erase history.","capabilities":["knowledge_write","append_only"],"risk":"local_write","approval_required":false,"executor":"ledger","tags":["remember","learn","knowledge","evidence"]},
    {"id":"nerves.trace","version":"1.0.0","organ":"nervous_system","description":"Record correlated execution, tool, approval, and evidence events.","capabilities":["trace","audit"],"risk":"local_write","approval_required":false,"executor":"ledger","tags":["trace","audit","event","observe"]},
    {"id":"immune.policy_check","version":"1.0.0","organ":"immune_system","description":"Evaluate tool, credential, network, approval, and environment policy before execution.","capabilities":["policy","security"],"risk":"read_only","approval_required":false,"executor":"internal","tags":["security","policy","permission","guardrail"]},
    {"id":"immune.skill_quarantine","version":"1.0.0","organ":"immune_system","description":"Quarantine newly discovered skills until source, checksum, license, permissions, and scripts are reviewed.","capabilities":["skill_review","supply_chain"],"risk":"local_write","approval_required":false,"executor":"internal","tags":["skill","install","discover","quarantine","supply-chain"]},
    {"id":"hands.code_patch","version":"1.0.0","organ":"hands","description":"Apply a bounded patch inside an isolated branch/workspace only.","capabilities":["code_write","patch"],"risk":"local_write","approval_required":false,"executor":"sandbox","tags":["code","patch","fix","implement","refactor"]},
    {"id":"hands.test","version":"1.0.0","organ":"hands","description":"Run declared compile/unit/integration checks in an isolated workspace.","capabilities":["test","shell"],"risk":"local_write","approval_required":false,"executor":"sandbox","tags":["test","pytest","compile","validate"]},
    {"id":"hands.security_scan","version":"1.0.0","organ":"hands","description":"Run defensive secret, dependency, SAST, and policy scans.","capabilities":["security_scan","shell"],"risk":"local_write","approval_required":false,"executor":"sandbox","tags":["scan","security","secret","audit","bandit"]},
    {"id":"legs.workspace_open","version":"1.0.0","organ":"legs","description":"Create or select an isolated local/E2B/Codespaces/Daytona workspace through the broker.","capabilities":["workspace","terminal"],"risk":"external_write","approval_required":true,"executor":"workspace_broker","tags":["workspace","terminal","codespace","sandbox"]},
    {"id":"legs.git_branch","version":"1.0.0","organ":"legs","description":"Create a feature branch without rewriting existing history.","capabilities":["git","branch"],"risk":"local_write","approval_required":false,"executor":"workspace","tags":["git","branch","upgrade","develop"]},
    {"id":"mouth.report","version":"1.0.0","organ":"mouth","description":"Produce a concise evidence-backed report or proposal.","capabilities":["report","explain"],"risk":"read_only","approval_required":false,"executor":"provider","tags":["report","summary","explain","proposal"]},
    {"id":"upgrade.self_improve","version":"1.0.0","organ":"nervous_system","description":"Run the governed self-upgrade lifecycle from discovery through evidence; production merge remains approval-gated.","capabilities":["self_upgrade","orchestration"],"risk":"high_impact","approval_required":true,"executor":"controller","tags":["upgrade","self-improve","develop","autonomous"]}
  ]
}
```
<!-- CKNEXUS_SKILL_MANIFEST_END -->

## Governed self-upgrade lifecycle

Discover → Verify source → Extract capability → Compare with current baseline → Create proposal → Risk review → Create isolated branch/workspace → Implement bounded change → Compile → Test → Security scan → Benchmark/eval → Build evidence → Council review → Human approval for merge/canary → Canary → Observe → Rollback on failure → Append learning.

The lifecycle may continue automatically through safe local development steps. It must stop before external/destructive/high-impact actions unless the relevant approval policy has already been satisfied.

## AGNES Execution Kernel Phase 1 — Security Baseline invariants

The R13 skill nervous system is extended, not replaced, by the execution security baseline:

- Agent != Executor.
- Workspace != Sandbox.
- Execution identity is frozen into one immutable manifest before execution.
- Approval is sticky to the exact execution fingerprint; changing inputs, permissions, workspace, baseline, credential requirements, executor, or policy invalidates the old approval.
- Executor risk can only raise effective risk, never lower it.
- Credentials remain behind Credential Broker leases; skills do not receive a bulk secret export.
- Kill switches exist at global, tenant, executor, and skill scopes.
- Results follow candidate -> verify -> scan -> approve -> promote; no direct production promotion.
- Phase 1 has no auto-merge and no auto-production deployment.
- The default Phase-1 executor registry is intentionally empty; missing executors fail closed.
