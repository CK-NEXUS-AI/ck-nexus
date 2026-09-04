# CK-NEXUS Master Work History & Connection Inventory — 2026-09-04

Status: OPERATING CONTEXT / SANITIZED INVENTORY
Policy: latest exact evidence wins
Secrets: intentionally excluded

## Authority state

- Frozen Q10 commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- Frozen Q10 tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`
- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

## Canonical GitHub

- Repository: `spinlnw10-art/ck-nexus`
- Visibility: private
- Default branch: `main`
- Main SHA: `b4146db8e23dff49520cbbc9d0194a15bcc5872d`
- Main tree: `25d9c74db2b553667ad085172f8ac7beff4146aa`
- Main commit signature state: unsigned
- ChatGPT GitHub connector permissions currently include read/write/admin-level repository capabilities.

### Current development PR snapshot

- PR #204 — OPEN / DRAFT / not merged
- PR #205 — OPEN / DRAFT / not merged
- PR #206 — CLOSED / not merged
- PR #207 — CLOSED / not merged
- PR #208 — OPEN / DRAFT / not merged
- PR #210 — OPEN / DRAFT / not merged
- PR #213 — CLOSED / not merged

## Q10 execution host / VPS

Known host:
- VM name: `10616a96dd5c121bb`
- Ubuntu 24.04.x LTS
- Linux kernel 6.8
- x86_64
- Docker available
- cgroups v2 measured PASS
- user namespace / `unshare -Ur` measured PASS
- bubblewrap basic sandbox measured PASS
- exact frozen Q10 canonical repository measured clean on host
- public SSH TCP/22 was independently measured reachable by GitHub Actions
- public IP and all credentials intentionally omitted from this document
- Remote Desktop Commander has been paired historically; latest connection state must be checked live before assuming access

Historical measured host resources:
- ~3.8 GiB RAM
- ~72 GiB root disk
- Docker 29.x observed
- systemd once reported degraded due to fwupd units
- 76 zombie processes were observed under a non-CK-NEXUS parent process and were not killed automatically

## ChatGPT-connected data sources

### Gmail
- Connector authenticated
- Account identity is intentionally masked in this document
- Used for Servermall support, Aikido, independent-review/certification outreach, GitHub notifications, provider replies
- Do not copy passwords, OTPs, API keys or sensitive provisioning credentials into evidence

### Google Drive
- Connector authenticated
- Current Drive connector is authenticated to a different Google account than the Gmail connector
- Account identity intentionally masked
- Use for user-approved file access and project documents when available

### GitHub
- Connector authenticated
- Repository access verified for `spinlnw10-art/ck-nexus`
- Used for branches, PRs, Actions, artifacts, code review and evidence collection

### Airtable
- Connector authenticated
- Accessible workspace permission: owner
- Known bases:
  - `CK-NEXUS Capability Stress Lab`
  - `CK-NEXUS Global Buyers & Security Partners`
- Current connector permission supports record creation in these bases

### Remote Desktop Commander
- Multiple historical devices are registered
- VPS device name: `10616a96dd5c121bb`
- Device IDs, session IDs and tokens intentionally omitted
- Connection state is ephemeral; always verify live before execution

## External services / evidence lanes

- Servermall — VPS provider/support ticket lane
- Aikido — supplemental security scanning / exact-commit gating candidate
- Schellman — independent software-security assessment outreach
- BSI / BSI Thailand — certification/assurance outreach
- Intertek Business Assurance — certification/assurance outreach
- NQA — certification/assurance outreach
- HackerOne — pentest request/outreach lane
- GitHub-hosted Actions — development CI, Docker helper farm, external network probes
- OpenAI Codex Security — authoritative Q10 native deep-scan requirement
- Darker — fresh verification step required after canonical scan

## Development/security work completed or measured

- Canonical main export and SHA-256 verification
- Recovery package reconciliation
- SYSTEM_MANIFEST / recovery governance work
- Docker full-capability development verification
- Semgrep / Trivy / Checkov / Gitleaks / ShellCheck / Hadolint preflight
- Syft CycloneDX SBOM
- Grype vulnerability cross-check
- Dependency-Check mirrored NVD mechanism test; coverage incomplete for Node dependency graph
- Q10 alternative-host qualification experiments
- Codex Security 0.1.24 Landlock compatibility candidate
- Knowledge Fabric V1 candidate
- Knowledge Persistence V2 with live PostgreSQL round-trip validation
- Creator Intelligence V1 research/mode-registry candidate
- Virtual Office / Human Control Surface specification
- Browser Live Console local candidate
- AGNES execution/security/governance development lanes

## Permanent operating rules

- Search first
- Delta only
- Reuse / deduplicate before rebuild
- Benchmark before adoption
- Security review before canonical adoption
- Independent verification before production authority
- Development evidence never auto-promotes to Q10 evidence
- Recovery evidence never auto-promotes to canonical runtime
- No AI self-approval
- No automatic Production merge/deploy
- No paid action without explicit human approval
- No credential exposure
- No fabricated evidence
- Latest exact evidence supersedes stale narrative

## Secret-handling rule

Never record or disclose:
- passwords
- API keys
- OTP / MFA codes
- private keys
- SSH private credentials
- OAuth refresh/access tokens
- Remote Desktop pairing codes/tokens
- provider provisioning secrets

Connection metadata may be recorded only when it is necessary and safe.

## Important connection nuance

Gmail and Google Drive are currently authenticated to different Google accounts.
Remote Desktop Commander connection state can change independently of SSH/network reachability.
A VPS may be reachable by SSH while the Remote Desktop Commander agent is offline.

## Current next priorities

1. Restore/verify persistent least-privilege VPS control path.
2. Complete Q10 host admission evidence.
3. Preserve exact Codex Security 0.1.24 authority unless governance explicitly changes it.
4. Run authoritative native Q10 deep scan only when quota/provider authority is valid.
5. Produce canonical Q10 artifacts.
6. Fresh Darker verification.
7. Independent HUMAN review.
8. Owner HUMAN sign-off.
9. Only then transition Q10 and unblock Q11/Q12.

This file is a sanitized operating inventory, not a credential store and not certification evidence.
