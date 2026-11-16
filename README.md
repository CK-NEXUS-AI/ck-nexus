# CK-NEXUS

**Governed Autonomous AI Operating System** — a self-hosted platform for AI orchestration, governed tool execution, persistent knowledge, and evidence-based operations.

CK-NEXUS is one platform with one canonical application runtime. **Agnes** is its AI orchestration and execution layer; the Creator Workspace is a user-facing workspace; and **/development** is an internal evidence dashboard. These are parts and interfaces of CK-NEXUS, not separate products or competing system identities.

> **Release decision: NO-GO for Production.** Do not treat a passing test subset, CI run, implemented feature, or running service as Production approval. The current release decision and gate evidence are maintained in [Release Status](RELEASE_STATUS.md) and the [Q10–Q16 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md).

## Start here

| Need | Open |
|---|---|
| Understand the system | [Unified Architecture](docs/CK_NEXUS_UNIFIED_ARCHITECTURE.md) · [Architecture](docs/ARCHITECTURE.md) |
| Run the application | [Quick start](#quick-start) · [Canonical Runtime Contract](docs/CK_NEXUS_UNIFIED_OPERATIONS_CONTRACT_V1.md) |
| See live development evidence | Start the Creator App and open **/development**; API: **/api/dev-status** |
| Understand Agnes and agent governance | [Agnes Master Upgrade](docs/CK-NEXUS-AGNES-MASTER-UPGRADE.md) · [Development Council](docs/DEVELOPMENT_COUNCIL.md) |
| Configure integrations | [Integration Hub](docs/INTEGRATION_HUB.md) |
| Review security and tests | [Security Audit](docs/SECURITY_AUDIT.md) · [Test Report](docs/TEST_REPORT.md) |
| Prepare a release | [Release Status](RELEASE_STATUS.md) · [Release Checklist](docs/RELEASE_CHECKLIST.md) · [Q10–Q16 Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md) |
| Prepare customer delivery | [Seller Checklist](docs/SELLER_CHECKLIST.md) |

## What CK-NEXUS provides

- **Agnes orchestration** — interprets requests, plans bounded work, coordinates specialist roles, and reports outcomes.
- **Governed execution** — permission checks, approval gates, isolated workspaces, bounded workers, idempotency, verification, and a kill switch.
- **Brain, memory, and knowledge** — session/context handling, knowledge retrieval, observations, and evidence-linked learning workflows.
- **Skills and capabilities** — discoverable capability contracts and adapters for approved tools.
- **Integration layer** — server-side connectors such as GitHub and model providers, mediated by the Credential Broker and CK-NEXUS policy.
- **Operations and evidence** — status APIs, audit records, test results, release subjects, and deployment evidence.
- **User workspace** — a web interface for interacting with CK-NEXUS capabilities.

These are capability areas of the same platform. A capability is not considered Production-ready merely because its code or documentation exists; its required runtime and release evidence must also pass.

## System architecture

~~~text
Users / API / Web Workspace
            |
       Agnes Orchestrator
            |
  Skills · Agents · Knowledge · Memory
            |
 CK-NEXUS Core / L3 Authority
 State · Permissions · Policy · Approvals
            |
 Governed Execution Kernel
 Queue · Sandbox · Idempotency · Verify
            |
 Approved Tool and Provider Adapters
 GitHub · Model Providers · MCP · Other Integrations
            |
 Evidence · Audit · Release Gates
~~~

**Authority boundary:** CK-NEXUS Core / L3 Authority owns state, memory, permissions, policy, execution decisions, and evidence. External tools and workflow services are adapters only; they do not become policy or release authorities. All consequential mutations must pass the applicable CK-NEXUS permission, approval, idempotency, and verification controls.

## Quick start

Requirements: Python 3.11 or later.

Linux / macOS:

~~~bash
cp .env.example .env.local
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e ".[dev]"
python3 -m creator_app.unified
~~~

Windows PowerShell:

~~~powershell
Copy-Item .env.example .env.local
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m creator_app.unified
~~~

Open http://127.0.0.1:8000. The canonical application entry point is:

~~~bash
python3 -m creator_app.unified
~~~

Legacy launchers may remain for compatibility, but new setup instructions and deployment definitions must use the canonical entry point and the [Canonical Runtime Contract](docs/CK_NEXUS_UNIFIED_OPERATIONS_CONTRACT_V1.md).

## Runtime and developer interfaces

| Interface | Purpose |
|---|---|
| GET /health | Application health/readiness endpoint |
| GET /api/status | Redacted application and configuration status |
| GET /docs | OpenAPI reference for the running build |
| /development | Internal development and evidence dashboard |
| GET /api/dev-status | Authenticated development-status snapshot |

The running build's OpenAPI document is authoritative for the complete API surface. Do not assume an endpoint or integration is available from a roadmap or historical report alone.

## Security and operating rules

- Keep production_status = NO-GO until every mandatory release gate is verified against the exact release subject and independently reviewed where required.
- Keep the MCP service bound to loopback (127.0.0.1:8765) under the current deployment contract; do not expose it directly to the public Internet.
- Keep credentials server-side in the approved credential mechanism. Never put keys, tokens, private keys, or secret values in source, README files, screenshots, or logs.
- Treat repository state, deployed runtime state, test results, and release evidence as separate facts; reconcile them before deployment.
- Do not reset, clean, overwrite, merge, or deploy over existing work without reviewing the exact diff and preserving required evidence.
- External tools have no CK-NEXUS policy authority. No evidence means no completion.

## Release readiness

Production promotion is fail-closed. The [Q10–Q16 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md) defines the mandatory security, live-provider, sandbox, recovery, observability, clean-machine deployment, and final-release evidence.

A release claim must identify the exact source commit, source tree, runtime/deployment subject, test and security reports, and required independent review. Evidence from a different commit or runtime is historical evidence, not proof for the candidate being released.

Run the repository's release check from the intended, clean release environment:

~~~bash
python3 scripts/release_check.py
~~~

Then follow the complete [Release Checklist](docs/RELEASE_CHECKLIST.md). A successful command is one piece of evidence, not a substitute for the full release decision.

## Current operational snapshot — 2026-11-17

This snapshot records the latest checks available for this maintenance update. It does not replace exact-commit release evidence or the [Q10–Q16 Closure Contract](docs/Q10_Q16_CLOSURE_CONTRACT.md).

| Area | Observed state | What it means |
|---|---|---|
| Production release | **NO-GO / NOT VERIFIED** | Q10–Q16 are not all closed with current, exact-subject evidence. |
| GitHub Actions | **BILLING LOCK REPORTED; PR CHECKS FAILURE** | The account/organization billing lock was reported in the latest operational handoff. Three PR #371 commit-associated runs currently show failure; the retrieved job summaries contain no step details, so their exact failure cause is not established here. |
| PR #369 | **OPEN; remote branch unchanged** | A remediation patch exists only in an isolated VPS worktree. It has not been pushed, committed to GitHub, or merged. |
| Local PR #369 verification | **PASS, local patch only** | 1,009 tests passed, 2 skipped; Ruff passed; Bandit reported 0 high/medium findings. These results do not certify the remote PR or current main. |
| Gitleaks | **REVIEW REQUIRED** | The latest local scan reported the empty CKNEXUS_ACCESS_TOKEN example in .env.example as a false positive; confirm scanner output before treating the scan as clean. |
| Q10–Q16 | **NOT VERIFIED for Production** | Do not promote a release based on the local PR test run or historical gate reports. |

The PR #369 local remediation patch and its verification record are stored on the VPS under:

~~~text
/opt/cknexus/evidence/pr369-remediations-20261117/
~~~

Patch SHA-256:

~~~text
1ddb0c591cb35b1514f41f77f3406c64d1b884d17f78094c74c5e72f4fe63c3a
~~~

This is local evidence only. The GitHub PR remains unchanged until a reviewed patch is deliberately committed and pushed. No merge or deployment is implied.

### GitHub Actions Billing Lock — Termux setup and safe checks

Install GitHub CLI in Termux:

~~~bash
pkg update -y
pkg install gh -y
gh auth login --hostname github.com --git-protocol https --web
gh auth status
~~~

Use the browser/device login flow where possible. Do not paste a personal access token into chat, a README, shell history, or logs. Do not print the token with gh auth token.

Check usage with the consolidated billing usage API. The older product-specific /settings/billing/actions endpoint has been retired:

~~~bash
gh api /users/USERNAME/settings/billing/usage
~~~

For an organization, use the documented organization endpoint. It requires organization-administrator access and an organization on the enhanced billing platform:

~~~bash
gh api /organizations/ORG/settings/billing/usage
~~~

The response contains usageItems; it does not use the old total_minutes_used field. The user endpoint also requires access to the enhanced billing platform; the organization endpoint requires organization-administrator access and enhanced billing. A 403 can indicate missing permission or platform eligibility; it does not prove that the Actions minutes quota was exhausted.

**Important:** Clearing Actions caches or deleting artifacts may reclaim storage, but it does not unlock a billing-locked account. Artifact deletion is irreversible. Changing a private repository to public is not a general Billing Lock fix and must not be done just to try to restart workflows.

The account or organization owner should open GitHub **Settings → Billing & licensing → Payment information**, review the billing notice/payment status, and follow GitHub's unlock instructions. If the billing page shows no actionable issue, contact [GitHub Support](https://support.github.com/contact). Do not retry blocked workflows until the billing lock is cleared.

After the owner confirms the account is unlocked, inspect recent runs:

~~~bash
gh run list --repo CK-NEXUS-AI/ck-nexus --limit 5
~~~

Only rerun a specific failed run after checking its cause and confirming the billing restriction is gone:

~~~bash
gh run rerun RUN_ID --repo CK-NEXUS-AI/ck-nexus
~~~

References: [GitHub CLI authentication](https://cli.github.com/manual/gh_auth_login) · [Billing usage API](https://docs.github.com/en/rest/billing/usage) · [Unlocking a locked account](https://docs.github.com/en/billing/how-tos/troubleshooting/locked-account) · [Removing workflow artifacts](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/remove-workflow-artifacts).

### Documentation freshness warning

At the time of this README update, RELEASE_STATUS.md still contains a 2026-10-31 baseline and historical commit/run references. Reconcile that document against the current repository head and newly generated Q10–Q16 evidence before using it as a current release attestation. This README intentionally keeps the conservative NO-GO decision and does not silently rewrite historical evidence.

## Engineering records

Implementation phases and historical milestones (including R-series and Agnes Execution Kernel phases) are documented as engineering records under [docs/](docs/). They describe the evolution and validation of individual capabilities; they are not separate products, runtime entry points, or independent Production certifications.

Useful references:

- [Agnes Execution Kernel Phase 3](docs/AGNES_EXECUTION_KERNEL_PHASE3_HARDENED_PIPELINE.md)
- [Credential Broker and Provider Router](docs/R7_CREDENTIAL_BROKER_PROVIDER_CUTOVER.md)
- [Canonical R9–R11 Implementation](docs/R9_R11_CANONICAL_IMPLEMENTATION.md)
- [Plans and reports](docs/plans/)
- [Repository Issues](https://github.com/CK-NEXUS-AI/ck-nexus/issues)
- [Repository Actions](https://github.com/CK-NEXUS-AI/ck-nexus/actions)

---

**Product identity:** CK-NEXUS.
**AI orchestration and execution layer:** Agnes.
**Canonical application runtime:** creator_app.unified.
**Current release decision:** NO-GO until the exact candidate passes all mandatory gates.
