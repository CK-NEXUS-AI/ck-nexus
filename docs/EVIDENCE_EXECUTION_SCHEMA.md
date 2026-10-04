# Evidence / Execution Data Contract

Logical data contract only; it does not claim every field is already persisted by the runtime.

## Execution

- execution_id
- agent_id
- lease_id
- policy_version
- approval_id
- credential_ref
- input_hash
- source_sha
- source_tree
- runtime_id
- started_at
- completed_at
- verification_status
- evidence_manifest
- final_verdict

## Evidence manifest

- evidence_id
- execution_id
- artifact_path
- artifact_sha256
- command
- exit_code
- environment
- actor
- timestamp
- verification_method
- status

## Rules

1. Credential references must not contain secret values.
2. Evidence must be bound to an exact source revision where source is relevant.
3. A final verdict must state its scope.
4. Missing required evidence prevents a DONE/VERIFIED claim.
