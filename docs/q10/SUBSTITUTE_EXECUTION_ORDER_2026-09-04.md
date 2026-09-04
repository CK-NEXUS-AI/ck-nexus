# CK-NEXUS Q10 Substitute Execution Order — 2026-09-04

Status: DEVELOPMENT / RESEARCH ONLY

Frozen Q10 subject:
- commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

Authority state remains:
- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

## Priority order

1. **Codex Security 0.1.24 + supported Landlock fallback**
   - Compatibility preflight passed on exact frozen subject.
   - This removes native bwrap/user-namespace as the only technical sandbox path.
   - Still requires governance acceptance for authoritative Q10 execution.
   - Do not change scanner version silently.

2. **Servermall VPS remediation**
   - Provider confirms VPS active and SSH endpoint available at `149.13.58.181:22`.
   - Remote Desktop Commander device is currently offline.
   - Next evidence needed from an available client network: ping/traceroute/TCP-22/verbose SSH diagnostics.
   - Do not expose credentials in logs or evidence.

3. **Aikido exact-commit gating as supplemental evidence**
   - Vendor confirms CLI API-key authentication and commit/release gating.
   - Free trial does not include audit-report export.
   - Machine-readable JSON is available in selected modes.
   - Use only if an API key is already available through an approved secret channel; never paste it into chat or evidence.
   - Aikido does not replace native Codex Security authority.

4. **OWASP Dependency-Check mirrored NVD feed**
   - Mirror mechanism solved cold-feed timeout.
   - Latest exact artifact: 8 dependencies, 0 vulnerabilities, but Node dependency coverage is incomplete because lockfiles/node_modules are absent.
   - Build a deterministic derived dependency graph or provide canonical lockfiles before relying on the result.

5. **WSL2 / Windows VPS candidate**
   - Reuse `infra/windows-vps-worker-bootstrap-v1` if a suitable Windows Server/VM is available.
   - Verify WSL2, nested virtualization, bwrap/Landlock behavior and exact subject binding before admission.

6. **Local Ollama/LM Studio**
   - Codex CLI supports local OSS providers.
   - Codex Security does not yet officially support arbitrary local OpenAI-compatible endpoints as an authoritative path.
   - State: `NO_SAFE_SUBSTITUTE_YET` for Q10.
   - Do not spend time building this route until official Codex Security support or an explicit governance exception exists.

## Human gates that cannot be substituted

- Independent HUMAN review
- Owner HUMAN sign-off
- External certification / accredited conformity assessment where required

## Rules

- latest exact evidence wins
- search first; do not repeat measured dead ends
- no paid action without explicit Owner approval
- no credential exposure
- Development evidence never auto-promotes to Q10 evidence
- no AI self-approval
