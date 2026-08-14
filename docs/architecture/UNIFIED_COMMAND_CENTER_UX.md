# CK-NEXUS Unified Command Center UX

Status: SPEC_ONLY / UI prototype branch

This document defines the professional web control surface for CK-NEXUS. It does not promote any production gate and does not grant runtime authority.

## Product model

CK-NEXUS should feel like one operations console, not a collection of unrelated pages. The operator should normally do four things: state a goal, observe system state, approve consequential actions, and verify evidence.

## Information architecture

Primary navigation:

1. Overview
2. AI / Agents
3. Workflows
4. Connections
5. Capabilities
6. Tasks / AGNES
7. Memory / Knowledge
8. Approvals
9. Evidence
10. Security
11. Observability
12. Recovery
13. Marketplace
14. Settings

Persistent global status:

- environment
- canonical source / release lineage
- system health
- Q01-Q16 gate state
- active executions
- pending approvals
- incidents
- provider/connector degradation
- cost/quota summary
- tenant/workspace/user

## Core page layout

Desktop uses a three-zone shell:

- left: persistent application navigation
- center: primary workspace
- right: contextual inspector

Mobile collapses navigation and inspector into explicit disclosure/dialog patterns while preserving the same task order.

## Overview

The default page answers five questions in under ten seconds:

1. Is the platform healthy?
2. What is running now?
3. What needs my approval?
4. What failed or degraded?
5. What evidence/gate state changed?

Required modules:

- System health summary
- Gate matrix Q01-Q16
- Active executions
- Pending approvals
- Connector health
- Incidents/alerts
- Event stream
- Cost/quota summary

## Human control model

Autonomy policy must be visible and understandable.

Suggested defaults:

- read-only discovery: AUTO
- analysis: AUTO
- draft generation: AUTO
- sandbox execution: AUTO within policy
- internal reversible writes: POLICY-BOUND
- external messaging: APPROVAL
- financial/billing actions: OWNER APPROVAL
- production mutation: OWNER APPROVAL
- security/permission changes: OWNER APPROVAL

No UI control may imply that a denied action succeeded. State labels must distinguish REQUESTED, PENDING_APPROVAL, RUNNING, VERIFIED, FAILED, BLOCKED and UNKNOWN.

## Approval Center

Every consequential approval card must show:

- exact action
- target
- actor/agent
- capability requested
- credential lease class (never secret value)
- risk level
- policy decision
- expected side effect
- reversibility/rollback path
- test/evidence summary
- expiry

Primary actions should be explicit verbs: Approve deploy, Reject request, Pause workflow. Avoid ambiguous Yes/No controls.

## Connections Center

Each connector/provider row exposes:

- lifecycle state
- health
- auth type
- permission scope summary
- capability count
- last successful probe
- rate/quota condition
- event subscriptions
- evidence link

Connect, Reconnect, Disconnect and Permission Change are separate operations. OAuth consent remains an owner action.

## AGNES task view

Show a task as a DAG plus an ordered human-readable execution timeline. Every node must expose:

- intent/goal
- chosen capability
- selected provider/tool/connector
- risk
- status
- retry/fallback history
- evidence
- resulting state transition

The operator can pause or terminate execution without opening developer tools.

## Evidence view

Evidence is first-class UI, not a hidden log page. Present:

- subject SHA/tree/manifest
- producer identity
- timestamp/freshness
- method/toolchain
- result
- scope
- limitations
- associated gate
- stale/valid state

Never merge "not tested", "not supported" and "failed" into one generic red status.

## Security Center

Security should include:

- authentication/session posture
- authorization/role posture
- credential lease posture
- security headers/CSP state
- dependency/supply-chain state
- scanner/evidence state
- incident state
- branch/release protection posture

Do not expose raw access tokens, refresh tokens, private keys or provider secrets.

## Accessibility target

Target WCAG 2.2 AA across responsive variants. Use semantic HTML first. Interactive widgets follow WAI-ARIA Authoring Practices when native HTML is insufficient.

Mandatory behaviors include:

- skip link
- visible keyboard focus
- logical source/focus order
- no keyboard traps except correctly implemented modal containment
- focus restoration after dialogs
- touch targets sized for reliable activation
- labels and programmatic names for controls
- status changes announced appropriately
- no meaning conveyed by color alone
- reduced-motion support

## Performance target

Field performance target at the 75th percentile on mobile and desktop:

- LCP <= 2.5 s
- INP <= 200 ms
- CLS <= 0.1

The command center should prefer server-rendered or progressively enhanced shells for critical state and avoid large client bundles for static operational panels.

## Security target

Use OWASP ASVS 5.0 as the web application verification baseline and OWASP Top 10:2025 as awareness coverage. Required browser controls include a deliberately tested CSP, correct MIME types, frame protection, referrer policy, protected caching for sensitive responses, strict origin/CORS policy and secure session handling.

## Design language

CK-NEXUS should remain typography-first and information-dense without becoming visually noisy.

Principles:

- clear hierarchy over decoration
- persistent status over transient toasts for important conditions
- one dominant action per panel
- explicit risk and environment labels
- progressive disclosure for expert detail
- tables for comparison, timelines for causality, graphs for topology
- calm default state; reserve strong emphasis for action-required conditions

## Non-goals of this prototype

- no production mutation
- no credential migration
- no replacement of existing Creator UI yet
- no Q10/Q11 promotion
- no claim of WCAG conformance until tested
- no claim of Core Web Vitals compliance until measured in field data
