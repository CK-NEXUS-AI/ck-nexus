# Tool 18 — LazyKeel
Research date: 2026-10-25. Search focus: exact name, deterministic supervision layer, offline/key-free CI gates and multi-agent supervision.

## 1. Identity
The exact product “LazyKeel” could not be uniquely verified from an authoritative primary source in this research pass. No canonical repository, official documentation, maintainer, license, release history or product page was found to substantiate the specified claims. Developer, launch year and current status are **No public evidence**. Do not assume it is the same as any similarly named package or commercial service.

## 2. Category
The requested description suggests a governance/verification supervisor for multi-agent workflows. Because the implementation was not identified, its category remains provisional rather than verified. Deterministic CI gates are a design pattern, not proof that a particular product implements them correctly.

## 3. Core Mechanism
No public evidence was found for LazyKeel's supervisor architecture, supported agent protocols, policy language, local/offline behavior or how it binds results to a specific commit. To qualify as a deterministic, key-free CI gate, the system should run without model credentials, consume immutable artifacts, return stable machine-readable outcomes, fail closed on missing checks, and record which exact commit was evaluated. These are proposed acceptance criteria, not product claims.

## 4. Key Capabilities
The requested claims—offline/key-free gates, multi-agent supervision and deterministic verdicts—remain unverified. Require source for its CI action, gate definitions, output schema, supported Git providers, failure semantics, and tests proving the verdict does not depend on an LLM response. If it merely asks an LLM to approve an agent, it does not meet the deterministic-supervision requirement.

## 5. Evidence
Searches for the exact name and feature phrases did not reveal an authoritative primary source. Benchmark, reliability, offline operation and customer evidence are therefore **No public evidence**. The closest verifiable proxy is the use of ordinary deterministic CI checks, branch protection, OPA/Conftest/Checkov and a versioned constraints registry; these provide known patterns but do not validate LazyKeel.

## 6. Limitations
Without a canonical source, security model, license, supply-chain provenance and data handling are unknown. A supervision layer that shares mutable state with the coding agent can be bypassed. A green status can also be misleading if tests are skipped, acceptance criteria are editable or the result is not tied to the tested commit SHA. Unknown maintenance status is itself a production risk.

## 7. Cost & Access
Pricing, install method, API-key requirements and self-hosting are **No public evidence**. Do not install or connect it to CK-NEXUS until the canonical repository is supplied, the license is checked and the project is inspected in an isolated environment. A claimed “key-free” gate should be tested with provider credentials removed from the environment.

## 8. Comparison
Compared with Constraints Registry, the latter has a public source repository and documented MCP/policy-validator integration. Compared with Qodo, Qodo has a commercial product page, documented toolbox and published pricing. This is a comparison of evidence and verifiability, not proof of relative performance.

## 9. Verdict
Do not adopt LazyKeel in production until identity and implementation are verified. For CK-NEXUS, the required behavior can already be approximated with existing CI, secret scanning, policy-as-code and Capability Authority checks; avoid adding a second supervisor without evidence it closes a measurable gap.

## Evidence gaps
All LazyKeel-specific claims in the request remain **No public evidence** in this pass.


### Minimum admission checklist
For the proposed offline CI behavior, test in an environment with DNS/network disabled and all model/API keys removed. The same commit and artifacts should produce the same verdict across repeated runs. A missing test binary, skipped test, malformed result or absent commit SHA should fail the gate rather than produce a success state. Multi-agent supervision should include concurrency locks, identity attribution, task cancellation, resource caps and a way to prevent one agent from approving its own output. Until the source code is found, these are requirements for an alternative implementation, not claims about LazyKeel.
