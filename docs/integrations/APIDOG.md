# CK-NEXUS x Apidog capability gateway

This integration keeps Apidog as a capability provider while CK-NEXUS remains the governance authority.

## Enabled integration surfaces

- API design / OpenAPI
- API test scenarios and suites
- Mock / sandbox workflows
- CLI / CI execution
- JUnit / HTML / CLI evidence
- Branch-aware API testing
- Future MCP specification access
- Enterprise audit/policy evidence where the Apidog plan supports it

Apidog CLI can manage API resources and execute test scenarios from CI/CD. Enterprise Audit Logs and Enterprise Policies are available on eligible Enterprise plans.

## Security boundary

The repository contains **no Apidog token**.

Required secret:

- `APIDOG_ACCESS_TOKEN`

The token must be stored as a GitHub Actions secret. Never commit it to source, workflow files, logs, or documentation.

## Current state

- Adapter workflow: IMPLEMENTED
- CLI installation path: IMPLEMENTED
- Evidence artifact upload: IMPLEMENTED
- Live Apidog execution: **NOT VERIFIED** until a valid secret, project ID, scenario ID, and optional environment ID are supplied.
- Production certification: **NOT CLAIMED**

## n8n role

n8n remains the orchestration layer. Its MCP server can expose selected workflows to AI clients, while CK-NEXUS keeps policy and evidence authority.

The n8n instance currently exposes CK-NEXUS workflows through MCP. Apidog is intentionally kept behind a credential boundary until an Apidog token and project identifiers are available.

## Activation gate

1. Add `APIDOG_ACCESS_TOKEN` to GitHub Actions Secrets.
2. Run `CK-NEXUS Apidog API Gate` manually with the real Apidog project/scenario/environment IDs.
3. Verify the CLI exit status.
4. Verify the JUnit/HTML artifacts.
5. Only then promote the capability from EXECUTED to VERIFIED.
