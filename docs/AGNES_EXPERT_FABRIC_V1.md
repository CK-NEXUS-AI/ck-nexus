# AGNES Expert Fabric v1

Status: CANDIDATE / MEASURED_NOT_VERIFIED ceiling until independent verification.

## Purpose

Expert Fabric adds a governed domain-expertise routing layer over capabilities that CK-NEXUS already has. It does **not** duplicate Council, Capability Registry/Router, AI Team, Dev Assistant Fabric, or Verification.

Existing AI Team roles are reused: Director, Engineer, Guardian, Analyst, Researcher, Designer, and Connector. An `IndependentVerifier` is represented as a role contract, not as an authority granted to the routing layer.

## Flow

`Task -> Domain Classification -> Risk Classification -> Existing Expert Selection -> Supporting Experts -> Policy/Approval Requirement -> Independent Verification Requirement`

The router is deterministic and recommendation-only. It cannot:

- grant or expand permissions;
- execute tools or external writes;
- merge or deploy;
- mutate production state;
- upgrade evidence to VERIFIED;
- allow a builder to self-approve.

## Initial domains

Security, architecture, backend, frontend, DevOps, data, AI/ML, research, UX, reliability, observability, compliance, legal, finance, business, integrations, and verification.

This list is intentionally extensible. Unknown domains fail safely to Director + Researcher discovery rather than inventing expertise.

## Risk policy

- LOW: expert recommendation only.
- MEDIUM: multi-domain coordination; Director may be added.
- HIGH: owner/policy approval and independent verification required.
- PRODUCTION: owner/governance approval and independent verification required; this layer never executes the production action.

Security, legal, and compliance routes are treated as HIGH by default. Production/deploy/release/merge terms are classified PRODUCTION.

## Search-first delta

Before this change, the repository already contained AI Team agents, automatic model routing, capability registry/router, council authority, dev assistants, connector fabric, and dynamic verifier. Therefore v1 deliberately implements only the missing coordination contract: **domain expertise selection with bounded-autonomy risk escalation**.

## Acceptance criteria

1. Existing AI Team agents are reused rather than cloned.
2. Unknown domains trigger discovery.
3. High-risk and production routes require independent verification.
4. Production routes require approval.
5. Router output has no execution/permission-grant/verified fields.
6. Routing is deterministic for the same input and registry version.

## Next integration after independent review

If accepted, integrate the route artifact with existing Capability Router and Council orchestration via an explicit adapter. Do not grant Expert Fabric direct execution authority.
