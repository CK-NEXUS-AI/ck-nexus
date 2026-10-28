# Universal AI Builder Connector (UABC)

Status: **initial registry and fail-closed capability facade implemented; provider adapters and live tests remain incomplete**.

## Scope and evidence model

- `config/uabc_platform_registry.json` is the machine-readable starting inventory. It separates public documentation status from actual adapter implementation. `adapter_implementation: planned` means no CK-NEXUS runtime adapter is available yet.
- `creator_app/universal_builder_connector.py` loads and validates the registry, provides platform discovery/details/capability inspection, normalizes connection status, gates operations by adapter-declared capabilities, requires explicit confirmation for mutating operations, and supports a process-local/environment kill switch.
- `tests/test_universal_builder_connector.py` covers registry validation, explicit unsupported outcomes, authorization failures, secret redaction, and the kill switch.
- The existing GitHub integration is wired as a read-only UABC adapter for authenticated connection checks. Existing OAuth, credential broker, vault, and Connector Fabric code should be reused when implementing more adapters; do not create a second credential store.

## Status semantics

Registry statuses describe the best currently recorded integration route, not the user's account state. `SUPPORTED_API` does not mean the UABC adapter is implemented or connected. A connection is `CONNECTED` only after a registered adapter verifies an authenticated request. Missing adapter/credentials are reported as `BLOCKED_AUTH` / `AUTH_REQUIRED` or `NOT_TESTED`; unsupported operations return `UNSUPPORTED_OPERATION` rather than a simulated success.

## Security requirements

- Provider credentials remain in CK-NEXUS's existing server-side credential broker/vault. Never put secrets in the registry, browser responses, tests, logs, or exported evidence.
- Provider adapters must use exact HTTPS host allowlists and the existing trusted-request security utilities where applicable; never accept arbitrary user-supplied outbound URLs with credentials.
- Do not scrape browser storage/cookies or bypass MFA, CAPTCHA, plan limits, or terms of service.
- Read-only actions may be automated only after adapter capability and authorization checks. Project creation/editing, exports, deployment, and disconnect require explicit confirmation; deployment/purchase actions also need policy-level approval.
- Set `UABC_KILL_SWITCH=true` to block outbound adapter checks/actions at process initialization. The runtime API for emergency shutdown is `disable_outbound()`.

## Coverage and limitations

The registry is an initial inventory, not exhaustive verified research. Official documentation links and plan/free-tier limits need per-provider validation and dated evidence. `free_tier` fields marked `VERIFY_*` are intentionally not claims of unlimited or permanently free service. Some provider URLs or product API scopes require verification before adapter work. No live API calls are performed by registry discovery.

## Verification

Run:

```bash
.venv/bin/python -m pytest -q tests/test_universal_builder_connector.py
.venv/bin/ruff check creator_app/universal_builder_connector.py tests/test_universal_builder_connector.py
python -m json.tool config/uabc_platform_registry.json >/dev/null
```

The live integration status remains `NOT_TESTED` until authorized provider credentials and a real provider adapter are available.
