# CK-NEXUS Development Preview Sales Package

## Sellable status

CK-NEXUS is sellable as a **Development Preview / Prototype / Custom Development Engagement**.

It is **not** sellable as a production-certified autonomous AI operating system yet.

## Recommended price

| Package | Price THB | What buyer gets |
|---|---:|---|
| Demo access / prototype walkthrough | 30,000–80,000 | Demo session, architecture explanation, roadmap |
| Installed development preview | 80,000–180,000 | VPS installation, Telegram control bridge, mock AI runtime, basic customization |
| Custom enterprise build | 200,000–500,000+ | Development contract, integrations, security hardening, deployment preparation |

Recommended current offer: **120,000 THB** for an installed development-preview system with further development scope.

## What is working now

- Windows VPS development worker is connected through Remote Desktop Commander.
- CK-NEXUS development runtime runs on the VPS.
- API status endpoint responds in mock mode.
- Authenticated `/api/runs` development smoke passes.
- Telegram bridge implementation exists in PR #131.
- Telegram bridge supports `/whoami`, `/help`, `/status`, `/health`, `/ask <text>`.
- Unknown Telegram chat IDs fail closed.
- Telegram `/ask` requires CK-NEXUS access token.
- Telegram outbound transport uses URL validation and `httpx`.
- Telegram token enrollment verifies Telegram `getMe` before authorization.
- Telegram token previously exposed in chat was removed and is not authorized.
- VPS local checks passed: Ruff, Bandit, Telegram tests 5/5.
- GitHub Development CI passed for the Telegram bridge branch.

## Explicit limitations

- Production remains **NO-GO**.
- Q10 Native Deep Security Scan is still required and not verified.
- Q11 Live Provider Smoke is blocked until Q10 passes.
- Q12 Linux sandbox evidence is blocked because Windows VPS cannot satisfy Linux cgroup v2 / namespace / seccomp evidence.
- Telegram live E2E requires the owner to regenerate and enter a new BotFather token directly on the VPS.
- OpenAI/live provider mode is not enabled for this development preview unless separately configured through a credential broker.

## Safe buyer wording

Use:

> CK-NEXUS is an enterprise AI-control-system prototype with a working VPS development runtime, Telegram control bridge, governed access model, and evidence-first production roadmap. It is available as a development preview and can be customized for organizational workflows.

Do not use:

> Production-ready autonomous AI operating system.

Do not claim:

- Q10 passed.
- Q11 passed.
- Q12 passed.
- Production approved.
- Fully secure.
- Provider/live AI verified.

## Delivery contents

- Source repository access or packaged source snapshot, depending on agreement.
- VPS installation notes.
- Telegram setup notes.
- Current evidence snapshot.
- Development roadmap and production closure gates.
- Buyer onboarding call.

## Next production milestones

1. Q10 Native Deep Security Scan on the frozen production subject.
2. Q11 Live Provider Smoke with brokered secrets after Q10 PASS.
3. Q12 Linux sandbox verification on a real Linux host.
4. Provenance reconciliation.
5. Final checksummed production package.
