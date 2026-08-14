# CK-NEXUS Capability Manifest Specification

Status: SPEC_ONLY
Version: 0.1

Every discoverable component MUST expose a machine-readable manifest. The manifest is declarative metadata; it does not itself grant execution authority.

## Required identity fields

- `id`: globally stable identifier, for example `github.connector`
- `version`: semantic version
- `type`: one of `provider`, `connector`, `tool`, `skill`, `agent`, `workflow`, `verifier`, `storage`, `policy`
- `display_name`
- `description`
- `owner`
- `lifecycle`: `experimental`, `candidate`, `canary`, `stable`, `deprecated`, `disabled`

## Capability declaration

Each capability MUST declare:
- capability ID
- semantic description
- input schema reference
- output schema reference
- side-effect class
- risk class
- idempotency support
- evidence requirements
- cost/quota metadata when relevant
- data classifications accepted/produced
- execution timeout hints

Recommended risk levels:
- `READ_ONLY`
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

Recommended side-effect classes:
- `NONE`
- `LOCAL_REVERSIBLE`
- `EXTERNAL_REVERSIBLE`
- `EXTERNAL_MUTATION`
- `DESTRUCTIVE`
- `FINANCIAL`
- `PRODUCTION_CONTROL`

## Authentication declaration

The manifest may advertise supported schemes, for example:
- oauth2
- api_key
- service_account
- github_app
- workload_identity
- mTLS
- local_socket
- none

Authentication metadata only informs Trust/Connection Fabric negotiation. Secrets are never stored in the manifest.

## Event declaration

A component declares event types it produces and consumes. Event names SHOULD be namespaced, versionable, and semantic, for example:
- `github.issue.created`
- `github.pr.created`
- `ck.task.assigned`
- `ck.execution.failed`
- `ck.evidence.accepted`

## Health declaration

Health metadata may include:
- probe type
- endpoint or internal function identifier
- timeout
- expected status contract
- degraded-state semantics
- minimum probe interval

Health success does not automatically mean authorization or policy eligibility.

## Trust requirements

Capabilities may require:
- tenant scope
- user scope
- approval class
- minimum trust level
- data-boundary policy
- credential lease class
- network zone
- sandbox class

## Evidence declaration

Consequential capabilities SHOULD declare required evidence collectors and validators, for example:
- request hash
- authorization grant ID
- execution receipt
- provider response hash
- external object ID
- postcondition readback
- policy decision hash
- timestamp/provenance attestation

## Example

```yaml
id: github.connector
version: 1.0.0
type: connector
display_name: GitHub Connector
description: Repository and collaboration operations
owner: ck-nexus
lifecycle: candidate

capabilities:
  repo.read:
    description: Read repository metadata and files
    risk: READ_ONLY
    side_effect: NONE
    input_schema: schemas/github-repo-read-input.json
    output_schema: schemas/github-repo-read-output.json
    idempotent: true
  issue.create:
    description: Create an issue
    risk: MEDIUM
    side_effect: EXTERNAL_MUTATION
    input_schema: schemas/github-issue-create-input.json
    output_schema: schemas/github-issue-create-output.json
    idempotent: conditional
    evidence:
      - execution_receipt
      - external_object_readback
  pull_request.create:
    description: Create a pull request
    risk: HIGH
    side_effect: EXTERNAL_MUTATION
    input_schema: schemas/github-pr-create-input.json
    output_schema: schemas/github-pr-create-output.json
    idempotent: conditional
    approval: change_control

auth:
  schemes:
    - oauth2
    - github_app
  secret_exposure: forbidden

risk_defaults:
  unknown_capability: deny

events:
  produces:
    - github.issue.created
    - github.pr.created
  consumes:
    - ck.task.assigned

health:
  kind: adapter_probe
  timeout_ms: 5000

trust:
  credential_lease_required: true
  tenant_bound: true
  raw_secret_to_model: forbidden

contracts:
  manifest_schema: schemas/fabric/capability-manifest.schema.json
```

## Discovery lifecycle

```text
manifest found
-> syntax validation
-> schema validation
-> signature/provenance check when available
-> capability normalization
-> contract compatibility check
-> security/policy classification
-> health probe
-> registry candidate
-> canary eligibility
-> active registration
```

A failed stage MUST NOT silently downgrade into active status.

## Compatibility rules

- Breaking input/output changes require a major version.
- Added optional fields may be minor-version compatible.
- Registry keeps multiple versions when required for workflow replay.
- Workflow state stores the exact manifest version selected at planning time.
- Execution re-validates that selected capability version is still allowed before dispatch.
- Deprecated capabilities may remain replayable but unavailable for new plans.

## Unknown fields and unknown capabilities

Parsers may preserve unknown fields for forward compatibility, but policy engines MUST fail closed when a security-critical or authorization-relevant field is unknown and required for safe execution.