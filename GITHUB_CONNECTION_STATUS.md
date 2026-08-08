# GitHub Connection Status

The GitHub connector used in this ChatGPT session authenticated successfully as `spinlnw10-art`.

Public/accessible repositories discovered during the connection check:

- `spinlnw10-art/websites` — default branch `master`
- `spinlnw10-art/openclaw` — default branch `main`

No CK-NEXUS repository was discovered, so this package does not guess which existing repository should be used.

Important: the ChatGPT GitHub connector credential is not exported into this source package. CK-NEXUS runtime authentication is intentionally separate. Configure a new GitHub App installation or a new fine-grained token in the VPS/server environment with `GITHUB_TOKEN`, then set `GITHUB_REPO=owner/repository`.
