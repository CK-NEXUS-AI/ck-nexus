# GitHub — Connect CK-NEXUS Runtime

GitHub support is built into this R2 package.

## Current connection state

The GitHub connector used in the ChatGPT session authenticated successfully as `spinlnw10-art`. Repositories discovered during verification were `spinlnw10-art/websites` and `spinlnw10-art/openclaw`. No CK-NEXUS repository was selected automatically.

The CK-NEXUS runtime does **not** receive or export the ChatGPT connector credential. Runtime authentication stays separate by design.

## Connect on your machine/VPS

Use a **new** GitHub credential. Do not reuse any token previously pasted into chat/logs.

```bash
sudo ./scripts/github/configure_github_env.sh /etc/cknexus/cknexus.env
```

The script asks for:

1. repository in `owner/name` form
2. GitHub token via hidden input

It writes the values to a mode-600 environment file and never prints the token.

Then start with that environment loaded. For Docker Compose:

```bash
set -a
. /etc/cknexus/cknexus.env
set +a
docker compose -f docker-compose.p0.yml up -d --build
```

Open `/demo` → `SYSTEM` → `TEST GITHUB`.

Or test via API:

```bash
export CKNEXUS_ACCESS_TOKEN='your-cknexus-access-token'
./scripts/github/test_github_via_api.sh
```

Expected result when complete:

```json
{
  "configured": true,
  "connected": true,
  "repository_access": true,
  "repository": "owner/repository"
}
```

The API never returns `GITHUB_TOKEN`.
