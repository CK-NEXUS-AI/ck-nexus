# CK-NEXUS × Apidog capability gateway

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

Apidog CLI can manage API resources and execute test scenarios from CI/CD. Enterprise Audit Logs and Enterprise Policies are available on eligible Enterprise plans. citeturn0search0turn0search1turn0search2

## Security boundary

The repository contains **no Apidog token**.

Required secret:

- `APIDOG_ACCESS_TOKEN`

The token must be stored as a GitHub Actions secret. Apidog documents that access tokens grant the account's Apidog permissions and should not be committed or exposed. citeturn0search7

## Current state

- Adapter code: IMPLEMENTED
- CLI installation path: IMPLEMENTED
- Evidence artifact upload: IMPLEMENTED
- Live Apidog execution: **NOT VERIFIED** until a valid secret, project ID, scenario ID, and optional environment ID are supplied.
- Production certification: **NOT CLAIMED**

## n8n role

n8n remains the orchestration layer. Its MCP server can expose selected workflows to AI clients, while CK-NEXUS keeps policy/evidence authority. citeturn0search4
