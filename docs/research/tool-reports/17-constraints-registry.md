# Tool 17 — Constraints Registry
Research date: 2026-10-25. Primary source: https://github.com/SureshKhemka/constraints-registry.

## 1. Identity
Constraints Registry (the repository's title uses “Constraint Registry” in places) is an open-source MCP server for policy-as-code guardrails for AI-generated code, maintained in the public `SureshKhemka/constraints-registry` repository. The README states Apache-2.0 licensing. It is an early-stage, actively developed project; verify exact release/tag and license before pinning it.

## 2. Category
Governance and verification infrastructure, not an autonomous coding agent. It supports AI-assisted and agentic coding by providing constraints and deterministic validation to agents such as Claude Code, Cursor and Codex.

## 3. Core Mechanism
The registry aggregates engineering constraints from source repositories into immutable, versioned, content-hashed bundles. An MCP server exposes tools such as `describe_scope`, `get_constraints` and `validate`. Constraints can be scoped by provider, resource type, environment and repository; precedence rules prevent a lower-priority source from weakening a higher-priority hard rule. Validation delegates to deterministic engines such as OPA, Conftest, Checkov and Semgrep. The README explicitly says the registry itself does not enforce constraints; it provides guidance and delegates enforcement. It also documents a fail-open behavior for `get_constraints`, which means a coding agent may still proceed if the guidance tool is unavailable. Critical rules therefore must also be enforced in CI/branch protection.

## 4. Key Capabilities
- Versioned and immutable constraint bundles.
- Multiple source repositories and precedence policy.
- Constraint querying via MCP at code-generation time.
- Artifact validation using deterministic policy/scanning engines.
- Importers for Checkov/Semgrep rule catalogs.
- Validation harness with schema, precedence, fixture and hot-reload checks.
- Integration instructions for Claude Code, Cursor and Codex.

## 5. Evidence
The official repository documents an example harness result of 21 passes, zero failures and zero skips for the bundled sample checks, while warning that optional external engines may be skipped if absent. That is evidence for the project's self-test harness at a particular setup, not a general security certification. The project docs also specify that OPA, Conftest and Checkov are optional, and checks for absent tools may skip. A production evaluation must inspect the harness JSON and fail if required validators were skipped. No independent enterprise deployment case study was found in this pass.

## 6. Limitations
The registry is not a security enforcement boundary by itself. Because guidance retrieval can fail open, agents can proceed without constraints unless a higher-level gate blocks them. Optional engines can lead to false confidence if skipped checks are ignored. Constraint source quality, precedence configuration and selector correctness remain operator responsibilities. MCP metadata itself can be poisoned or changed, so pin versions, diff tool schemas and require review for updates.

## 7. Cost & Access
The repository is Apache-2.0 and can be self-hosted. The README requires Python 3.11+, `uv`, and Semgrep through the Python environment; OPA is required for the reference Rego enforcement path, while Conftest and Checkov are optional. Software license cost is $0, but running validators and maintaining policy repositories cost engineering time and compute. Install and run the official harness before connecting agents. Source: https://github.com/SureshKhemka/constraints-registry.

## 8. Comparison
Compared with Qodo, Constraints Registry provides versioned constraints and deterministic validators rather than a managed probabilistic code-review platform. Compared with OPA/Conftest alone, it adds an MCP query surface and multi-source constraint bundle for coding agents, but still relies on underlying enforcement engines for actual decisions.

## 9. Verdict
Strong low-cost candidate for CK-NEXUS because it can expose engineering constraints to existing agents without replacing the current Council. Start with a read-only local MCP integration, require hard policies to run in CI, and treat missing validators as a failure when the policy is security-critical. Keep it bound to `127.0.0.1` or stdio unless authenticated remote transport is explicitly secured.

## Evidence gaps
No independent evidence found here for production incident reduction. The README's harness counts must be reproduced on the pinned version with all required engines installed.
