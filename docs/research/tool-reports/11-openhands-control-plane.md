# Tool 11 — OpenHands Agent Control Plane
Research date: 2026-10-25. Primary sources: https://www.openhands.dev/enterprise, https://hub.openhands.dev/blog/agent-control-plane, https://www.openhands.dev/pricing.

## 1. Identity
The OpenHands Agent Control Plane is the enterprise governance/orchestration layer from the OpenHands project. It is distinct from the open-source single-user agent runtime and is offered under a commercial enterprise model. The enterprise site documents private-VPC/Kubernetes deployment, integrations and organizational controls; exact license and contract terms depend on the selected product.

## 2. Category
Multi-Agent orchestration and governance. It supervises agents and execution environments rather than being just another coding model. It is not a self-evolving coding system by itself.

## 3. Core Mechanism
OpenHands describes three layers: agent harness, orchestrator/runtime environment, and control plane. The control plane governs which users can start agents, what they can access, where work runs, budgets, policies and auditability. It can trigger workflows from GitHub, Slack, Jira or schedules, run agents in isolated containers and return PRs for review. The enterprise architecture lists RBAC, guardrails, reporting/observability, LLM gateway, budgeting, context layer, APIs and automations. This is broader than a single coding agent because it provides shared operational controls across workflows and potentially external agents.

## 4. Key Capabilities
- Multi-user RBAC and centralized policy controls.
- SAML/SSO and enterprise access governance.
- Budget and usage monitoring.
- Audit and observability across agents and workflows.
- Integrations with GitHub, GitLab, Slack, Jira and other systems.
- Self-hosted deployment in a private VPC/Kubernetes environment.
- Ability to govern recurring and event-driven agent runs.

## 5. Evidence
The official enterprise page and April 3, 2026 control-plane article describe the product model and supported features. This establishes vendor-documented capability, not an independent audit of each control. No public evidence was found in this pass of an independent comparative study proving a specific cost reduction or security improvement over a custom control plane. Validate SSO/RBAC enforcement with negative tests and audit-log inspection in a trial environment.

## 6. Limitations
Enterprise functionality is not equivalent to free open-source deployment. A control plane can centralize policy but cannot compensate for weak runtime isolation, overbroad secrets, unsafe network egress or poor acceptance tests. External agents may retain their own authentication, tools and execution semantics. Budgeting can limit spend but does not prove task correctness. Self-hosting adds operational burden for upgrades, storage, network, identity and disaster recovery.

## 7. Cost & Access
OpenHands local OSS is free; enterprise control plane pricing is custom according to the official pricing page. Enterprise supports self-hosting in a VPC and BYOK. Deployment may require Kubernetes/containers, identity integration and model-provider keys. Sources: https://www.openhands.dev/pricing and https://www.openhands.dev/enterprise. No public fixed price should be invented.

## 8. Comparison
Compared with Hive, OpenHands positions a general-purpose enterprise control plane across agent workflows and vendors; Hive is focused on repository co-maintenance and ACMM maturity profiles. Compared with a custom CK-NEXUS authority layer, OpenHands may reduce the work needed for enterprise identity and operations, but could duplicate the existing Council Capability Authority, MCP gateway, watchdog and evidence contracts.

## 9. Verdict
Consider for a mid-size/enterprise team that needs RBAC, SSO, budgets, audit and multi-agent operations across repositories. For CK-NEXUS, compare the commercial control plane with the existing capability authority before adoption; do not run two competing policy authorities. Keep the existing signed, one-time capability grants as the execution boundary unless a documented migration proves equivalence.

## Evidence gaps
No public evidence found here proves a guaranteed reduction in incidents or cost. Confirm product tier, contractual data terms, external-agent coverage and security-control behavior in a proof of concept.


### Enterprise fit checks
The feature list should be validated with acceptance tests rather than screenshots: an unauthorized user must be unable to launch a session, a budget-exhausted user must be blocked, an agent must not read another user's workspace, and audit entries must identify the actor, tool, target resource and result. Test whether external agents inherit the same policy or run under separate controls. A control plane is valuable only when it governs the actual execution path; dashboards that merely report after the fact are observability, not prevention.
