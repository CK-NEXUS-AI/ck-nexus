# Unified Command Center Contract Mapping

Status: architecture/UI integration map.

## Rule

Every screen is a projection of normalized CK-NEXUS contracts. A UI button submits a Control Plane command; it does not call provider SDKs, secret stores or production infrastructure directly.

## Screen mapping

- Overview -> health/SLO, incidents, AGNES task summaries, approvals, evidence gate summaries, budget/quota observations.
- AI / Agents -> Cognitive Governor decisions, worker scorecards, agent/skill capability manifests, evaluation state.
- Workflows -> Automation Fabric definitions, Task DAG templates, trigger/rule state, compensation policies.
- Connections -> connector lifecycle + authorization + health + semantic capability verification.
- Capabilities -> registry candidates, lifecycle, score/evidence, provider/connector implementations and policy eligibility.
- Tasks / AGNES -> task/node/attempt state, plan hash, capability decisions, execution receipts, pause/cancel/reconcile controls.
- Memory / Knowledge -> provenance-backed memory/claims, retention, freshness, conflicts and source access.
- Approvals -> approval requests, exact action/target/plan/risk/environment/cost/expiry and explicit approve/reject commands.
- Evidence -> gate mapping, subject digests, evidence freshness, provenance and execution receipts.
- Security -> policy decisions, security vetoes, credential lease metadata/redacted connection state and supply-chain findings.
- Observability -> SLO status, metrics/traces/logs/events, alert/incident correlation, cost/quota.
- Recovery -> incidents, backup manifests, recovery drill state, rollback/compensation requests.
- Marketplace -> artifact identity/digests, requested capabilities/permissions, admission lifecycle, canary/stable/revoked state.
- Settings -> tenant policy/preferences/autonomy ceilings; credential values remain outside general UI.

## UI state semantics

Never render `connected`, `healthy`, `approved`, `cancelled`, `restored`, `deployed` or `PASS` based only on a request being accepted. UI state comes from authoritative normalized state plus freshness.

## Command UX

Consequential controls show exact verb, target, environment, expected effect, reversibility/compensation, risk, permission delta, budget impact, evidence/precondition summary and approval class. Stale object versions are rejected and UI refreshes before retry.

## Live updates

Event streams improve responsiveness, but clients reconcile authoritative current object after gaps/reconnect. Events carry correlation/causation IDs and never expose secrets.

## Mobile/accessibility

Core status, task controls and approval review remain usable on narrow screens and keyboards. WCAG 2.2 AA remains target; reduced motion and semantic/native controls are preferred.
