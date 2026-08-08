# CK-NEXUS GitHub Integration

CK-NEXUS can connect to GitHub automatically at startup without embedding a credential in source code.

## Runtime configuration

Set these values in the protected server/VPS environment, not in Git:

```bash
export GITHUB_TOKEN='YOUR_NEW_FINE_GRAINED_TOKEN'
export GITHUB_REPO='owner/repository'
```

Optional for GitHub Enterprise/API proxies:

```bash
export GITHUB_API_BASE='https://api.github.com'
```

Then start CK-NEXUS normally and open `/demo` → `SYSTEM` → `TEST GITHUB`.

The UI reports one of:

- `CONNECTED` — authentication and repository access both verified.
- `CONNECTED / NO REPO ACCESS` — authentication works, but `GITHUB_REPO` is unset or the token/app lacks access.
- `NOT CONFIGURED` — `GITHUB_TOKEN` is absent.
- `AUTH FAILED` — token was rejected.

The server never returns or logs the token value through the GitHub status endpoint.

## Important

Do not reuse a token that has already been pasted into chat, logs, screenshots, tickets, or public files. Revoke it and create a new fine-grained token or use a GitHub App installation with only the repository permissions CK-NEXUS needs.
