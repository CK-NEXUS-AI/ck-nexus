# CK-Codex Account Switcher

Purpose: manage multiple **independent Codex CLI login profiles** without copying, merging, or exposing credentials.

## Security model

- Each account gets a separate `CODEX_HOME` directory.
- The user performs the official `codex login` flow themselves.
- The tool never asks for or stores a Gmail password, OTP, API key, or refresh token in its own metadata.
- Switching is implemented by selecting a different `CODEX_HOME`; it does not bypass OpenAI authentication.
- Account profiles are local to the machine and should be permissioned 0700.
- Never print the contents of a Codex credential file.

## Commands

From the repository root:

```bash
python tools/ck-codex-account.py list
python tools/ck-codex-account.py add work
python tools/ck-codex-account.py login work
python tools/ck-codex-account.py status work
python tools/ck-codex-account.py env work
python tools/ck-codex-account.py run work -- codex --version
```

`login` launches the official interactive Codex authentication flow with that profile's `CODEX_HOME`.

`env` prints shell-safe environment assignments for manual activation:

```bash
eval "$(python tools/ck-codex-account.py env work)"
codex login status
```

For a one-shot command, prefer `run` so the parent shell environment is unchanged:

```bash
python tools/ck-codex-account.py run work -- codex login status
```

## Evidence

The switcher records only profile metadata (name, created/updated timestamps, active profile marker). It does not record credentials or tokens.

This is a **Codex CLI profile switcher**, not a ChatGPT account merger and not a mechanism for bypassing Codex client/workspace restrictions.
