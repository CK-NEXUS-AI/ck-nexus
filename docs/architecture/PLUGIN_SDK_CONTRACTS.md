# CK-NEXUS Plugin SDK Contracts

Status: SPEC_ONLY
Version: 0.1

Plugin SDKs provide narrow, provider-neutral interfaces. The orchestrator reasons about capabilities and contracts; it does not know vendor SDKs.

## Common plugin contract

All plugin families SHOULD expose:

```python
from typing import Protocol

class Plugin(Protocol):
    plugin_id: str
    version: str

    async def manifest(self) -> dict: ...
    async def health(self) -> "HealthStatus": ...
    async def close(self) -> None: ...
```

Registration is separate from execution authority. A plugin can be installed and healthy but still denied by policy.

## ProviderPlugin

```python
class ProviderPlugin(Protocol):
    plugin_id: str

    async def capabilities(self) -> "ProviderCapabilities": ...
    async def health(self) -> "HealthStatus": ...
    async def estimate_cost(self, request: "GenerateRequest") -> "CostEstimate": ...
    async def generate(self, request: "GenerateRequest") -> "GenerateResult": ...
    async def stream(self, request: "GenerateRequest"): ...
```

Normalized result SHOULD include model/provider identity, token/usage metadata when available, latency, finish reason, structured output, citations/evidence references when supported, and policy-safe error classification.

Providers never receive connector credentials unless a separately governed tool invocation contract explicitly requires an authorized brokered token.

## ConnectorPlugin

```python
class ConnectorPlugin(Protocol):
    plugin_id: str

    async def capabilities(self) -> "ConnectorCapabilities": ...
    async def auth_requirements(self) -> "AuthRequirements": ...
    async def health(self, lease: "CredentialLease | None") -> "HealthStatus": ...
    async def execute(self, request: "ConnectorRequest", lease: "CredentialLease") -> "ConnectorResult": ...
    async def verify(self, receipt: "ExecutionReceipt") -> "VerificationResult": ...
```

Connector `execute()` is reachable only through AGNES guarded execution. It does not own approvals, credential storage, or release policy.

## ToolPlugin

Tools expose bounded operations that may be local or remote. Each tool declares side effects, sandbox needs, network requirements, and evidence expectations.

```python
class ToolPlugin(Protocol):
    plugin_id: str

    async def capabilities(self) -> "ToolCapabilities": ...
    async def invoke(self, request: "ToolRequest", context: "ExecutionContext") -> "ToolResult": ...
```

## SkillPlugin

Skills transform intent/context into structured intermediate work and SHOULD be side-effect free by default.

```python
class SkillPlugin(Protocol):
    plugin_id: str

    async def describe(self) -> "SkillDescriptor": ...
    async def run(self, request: "SkillRequest", context: "SkillContext") -> "SkillResult": ...
```

If a skill needs external mutation, it must return an execution proposal/task rather than directly mutating the external system.

## AgentPlugin

Agents can plan/delegate but cannot bypass Trust Fabric.

```python
class AgentPlugin(Protocol):
    plugin_id: str

    async def profile(self) -> "AgentProfile": ...
    async def propose(self, task: "Task", context: "AgentContext") -> "AgentProposal": ...
```

Agent outputs are proposals. AGNES is the side-effect boundary.

## VerifierPlugin

```python
class VerifierPlugin(Protocol):
    plugin_id: str

    async def verify(self, claim: "Claim", evidence: list["EvidenceRef"]) -> "VerificationResult": ...
```

Verifiers should be independently replaceable from executors to avoid the same component proving its own side effect without external confirmation.

## WorkflowPlugin

A workflow plugin supplies declarative DAG templates, trigger contracts, compensation semantics, and required policy classes. Workflow plugins do not store credentials.

## EvidenceCollectorPlugin

Collectors normalize receipts/readbacks/logical proofs into Evidence Fabric records. They may collect but may not mark their own evidence as release-accepted.

## StoragePlugin

Storage plugins provide semantic capabilities such as transactional state, lease/lock, event append, object evidence, vector retrieval, or graph traversal. Higher layers select by capability rather than database brand.

## Error contract

All plugin families SHOULD normalize failures into stable classes:
- transient_network
- rate_limited
- auth_refreshable
- auth_owner_action_required
- permission_denied
- policy_denied
- invalid_request
- contract_mismatch
- dependency_unavailable
- side_effect_uncertain
- permanent_failure

Vendor-specific error details may be preserved as redacted metadata.

## Cancellation and timeout

Plugins must honor bounded execution time and cancellation where the underlying provider supports it. Timeout policy belongs to the execution context, not hardcoded plugin globals.

## Credential rules

- Plugin interfaces receive opaque credential leases/handles where possible, not long-lived raw secrets.
- Plugins MUST NOT persist raw leased secrets in logs, events, evidence payloads, model context, or application databases.
- Refresh/rotation is owned by Credential Broker/Trust Fabric using official mechanisms.

## Compatibility

Each SDK family maintains contract versions separately from plugin implementation versions. Registry resolution checks both before selection.

## Testing

Every plugin candidate SHOULD pass:
- manifest schema validation
- SDK contract tests
- negative/error tests
- timeout/cancellation tests
- credential redaction tests
- risk/side-effect declaration checks
- idempotency tests where applicable
- postcondition/evidence tests for external mutations