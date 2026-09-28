---
name: account-switcher
description: Safely add, authenticate, inspect, and switch isolated Codex CLI login profiles using separate CODEX_HOME directories.
---

Use this skill when the user wants to use another Google/Gmail account with Codex CLI, switch between Codex accounts, or verify which isolated Codex profile is active.

## Workflow

1. Treat the account name as a local profile label, not as a credential.
2. Use `tools/ck-codex-account.py add <name>` to create an isolated profile.
3. Use `tools/ck-codex-account.py login <name>` to start the official Codex login flow. The user must select the intended Google account and approve access in the provider UI.
4. Never ask the user to paste a password, OTP, refresh token, API key, or credential-file contents into chat.
5. Verify with `tools/ck-codex-account.py status <name>`.
6. Switch for a single command with `tools/ck-codex-account.py run <name> -- <command>`, or activate the shell with `eval "$(tools/ck-codex-account.py env <name>)"`.
7. Report evidence separately from claims: profile created, login command completed, status output, and command execution are distinct states.

## Safety boundaries

- Do not merge accounts.
- Do not copy credential files between profiles.
- Do not bypass OpenAI authentication or subscription/usage controls.
- Do not print or log credential contents.
- Removing a profile requires an explicit `--confirm`.
- If the official Codex login flow fails, preserve the profile and report the failure rather than attempting an alternate authentication path.

## Expected result

The selected profile has its own `CODEX_HOME`, so Codex uses that profile's own authentication state while the parent shell remains unchanged for one-shot commands.
