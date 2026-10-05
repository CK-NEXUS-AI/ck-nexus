# CK-Codex Account Switcher

A small, security-first helper for using more than one Codex CLI login on the same machine.

## What it does

It isolates each login in its own `CODEX_HOME`:

```text
~/.ck-codex-accounts/
  accounts.json
  profiles/
    personal/
    work/
    second-gmail/
```

The official Codex CLI owns the credentials. CK-Codex only selects which profile directory is active.

## Quick start

```bash
python tools/ck-codex-account.py add personal
python tools/ck-codex-account.py login personal

python tools/ck-codex-account.py add second-gmail
python tools/ck-codex-account.py login second-gmail

python tools/ck-codex-account.py list
python tools/ck-codex-account.py run second-gmail -- codex login status
```

The `login` command opens the official Codex authentication flow. Select the intended Google account in the browser and approve the requested access yourself.

## Switching

For one command:

```bash
python tools/ck-codex-account.py run second-gmail -- codex exec --sandbox read-only "Review this repository."
```

For the current shell:

```bash
eval "$(python tools/ck-codex-account.py env second-gmail)"
codex login status
```

The helper cannot merge ChatGPT accounts, transfer subscriptions/credits, or bypass OpenAI authentication. It is deliberately limited to selecting an isolated Codex CLI login profile.

## Safety

- No password or OTP input is accepted by the helper.
- API-key environment variables are removed from child Codex processes.
- Profile and metadata directories are permissioned 0700/0600.
- Removing a profile requires explicit `--confirm`.
- Credential files are never printed.
