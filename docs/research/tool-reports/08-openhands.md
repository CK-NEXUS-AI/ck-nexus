# Tool 08 — OpenHands / OpenDevin
Research date: 2026-10-25. Primary sources: https://github.com/All-Hands-AI/OpenHands, https://github.com/OpenHands/docs, https://www.openhands.dev/pricing, https://www.openhands.dev/enterprise.

## 1. Identity
OpenHands is an open-source AI software-development agent project that evolved from the OpenDevin project name. The core open-source offering is MIT-licensed according to its official pricing documentation; commercial enterprise offerings are separate. The project is active and offers CLI, web UI, SDK, local runtime and hosted/enterprise options.

## 2. Category
Task Agent with orchestration and collaboration options. Multi-agent use is possible through the SDK/automation architecture, but an individual agent session is still a task agent. It is not inherently self-evolving; continuous improvement requires tests, monitoring and safe iteration controls.

## 3. Core Mechanism
OpenHands separates the agent from the execution runtime. The agent produces actions; an event stream passes them to a runtime that executes shell commands, browser actions and other tools inside a Docker sandbox. The runtime returns observations for the next loop iteration. This separation supports reproducibility and resource isolation. Enterprise offerings add a control plane, policy and observability layers, integrations, RBAC and budgeting. Docker isolation is a security improvement, not a guarantee: mounts, secrets, container privileges and network settings determine actual exposure.

## 4. Key Capabilities
- Open-source local execution with web UI, terminal UI and CLI.
- Model-agnostic design and BYOK.
- Git integrations and SDK for automation.
- Docker sandbox runtime to isolate agent code execution.
- Enterprise self-hosting in a private VPC/Kubernetes, RBAC, SSO, multi-user controls, reporting, budgeting and integrations.
- Workflow triggers from issues, chat or schedules can result in PRs for review.

## 5. Evidence
Official docs explain the Docker runtime architecture and product tiers. The pricing page lists the local open-source option as free and self-hostable, and enterprise as custom-priced with VPC/self-host options. This is stronger evidence for deployability than vendor marketing about productivity. SWE-bench scores depend on the model, agent version, benchmark split and evaluation method; do not cite a single score as a property of the project across versions. No independent benchmark claim is made here without a pinned run configuration.

## 6. Limitations
Self-hosting transfers responsibility for patching, monitoring, network policy, authentication, storage, secret management and scaling to the operator. A Docker sandbox can still exfiltrate any data mounted or reachable over the network. Running many concurrent sessions consumes CPU, RAM, disk and model tokens; the CK-NEXUS VPS previously measured at roughly 1 vCPU and under 2 GiB RAM is not a sensible place to deploy a large multi-user agent fleet without capacity planning. Provider quotas and API costs remain even when the orchestration code is free.

## 7. Cost & Access
Open-source local edition: $0 plus compute and model costs. Individual cloud tier has a free entry option and supports BYOK or provider usage at cost; the official page lists a 10-conversation daily maximum for the Individual hosted tier. Enterprise is custom priced and supports self-hosting in a VPC, RBAC, SAML/SSO and integrations. Source: https://www.openhands.dev/pricing and https://www.openhands.dev/enterprise. Install through the official repo/docs or Docker/CLI path; pin image tags and review permissions before running untrusted code.

## 8. Comparison
Compared with Devin, OpenHands provides more control and self-hosting but requires more operational ownership. Compared with Codex CLI, OpenHands offers a provider-agnostic web/SDK runtime and enterprise control plane; Codex has a tighter OpenAI integration and open harness. For a small VPS, a single low-concurrency worker is safer than a large always-on fleet.

## 9. Verdict
Best for teams needing inspectable agent infrastructure, provider flexibility and the option to self-host. Not appropriate to install blindly into production or expose the web UI publicly without authentication and network hardening. For CK-NEXUS, consider OpenHands as a candidate isolated worker in a dedicated container/host only after measuring resource use, adding per-task workspaces, restricting egress and validating artifact/test evidence.

## Evidence gaps
Official architecture proves the intended runtime model, not that every deployment is securely configured. No public evidence here establishes one universal SWE-bench score or a guaranteed production completion rate; benchmark numbers must be tied to exact model and harness versions.
