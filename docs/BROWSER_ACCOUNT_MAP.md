# CK-NEXUS Browser & Account Map

Updated: 2026-10-26
Purpose: reduce account confusion and prevent closing active sessions.

## Verified account/service mapping

- ChatGPT GitHub Connector: authenticated as `spinlnw10-art` in the connector evidence. This is separate from VPS Git authentication and does not prove access to `CK-NEXUS-AI/ck-nexus`.
- Linux VPS Git remote: `https://github.com/CK-NEXUS-AI/ck-nexus.git`. Current repository checkout is `/root/ck-nexus`; current local branch was `main`, one commit ahead of `origin/main` at the last observed check. Do not push or reconcile automatically.
- CK-NEXUS GitHub runtime auth: documented as environment-based `GITHUB_TOKEN` + `GITHUB_REPO`; runtime credential state must be verified without printing values.
- n8n: runs on Linux VPS; Qwen Chat UI candidate is an inactive JSON export and must remain inactive until credentials, missing dependency, HTTP methods, and acceptance tests are verified.
- Model Studio/Qwen: provider env files exist, but existence does not prove keys are populated or inference succeeds. Never reveal secrets; validate key presence/health only.
- Windows VPS: Chrome and Edge user-data directories both exist. Chrome includes Default and Profile 1; Edge includes Default. Actual signed-in identities and open-tab titles were not verified.
- Linux VPS: CK-NEXUS managed browser is a separate headless Chrome profile at `/var/lib/cknexus-browser/profile`, remote debugging bound to loopback `127.0.0.1:9222`. Do not confuse it with Windows interactive Chrome/Edge.
- Termux: separate device/repository. Do not assume its browser login or Git credentials match either VPS.

## Browser assignment rules

1. Use the connected ChatGPT browser only for ChatGPT UI tasks; current session cannot enumerate tabs unless its originating browser context/extension is available.
2. Use Linux VPS managed headless Chrome only for CK-NEXUS-controlled browser automation, through its authorized local interface. Never expose CDP publicly.
3. Use Windows Chrome/Edge only after identifying the intended profile and signed-in account. Prefer one designated CK-NEXUS work profile and keep personal sessions separate.
4. Use the browser in which the required provider account is already authenticated; never switch accounts blindly.
5. Do not infer an account from a browser executable or profile folder. Verify the account identity from the site UI when authorized.

## Tab cleanup rules

- Keep only tabs needed for the current task, but inspect tab titles and preserve unsaved forms, active editors, OAuth consent flows, n8n executions, remote desktop sessions, and pages with unsaved changes.
- Close only clearly redundant/idle tabs after their purpose is verified. Never terminate all Chrome/Edge processes to reduce tab count.
- If tab inventory or GUI control is unavailable, report BLOCKED and do not guess which tabs are safe to close.
- Prefer Chrome profiles to separate work/personal identities; Chrome profiles keep browser data separate. Official reference: https://support.google.com/chrome/answer/2364824

## Current limitations (2026-10-26)

- Browser connector returned: “Browser access requires the originating browser context.” Open-tab list unavailable in this session.
- Windows process inventory shows many Chrome processes but does not establish tab count, tab titles, or which tabs are safe to close.
- No tabs were closed, no browser process was terminated, and no login/session was changed.
- Next action: establish authorized browser tab inventory/control, map each required service to the intended signed-in account, then close only confirmed redundant tabs and verify afterward.
