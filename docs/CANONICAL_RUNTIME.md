# CK-NEXUS Canonical Runtime Contract

**Contract status:** implementation baseline for launch-path consistency. This document does not
change security, Q10-Q16, production-readiness, or release-approval decisions.

## Single application composition root

`creator_app.unified` is the only supported application composition root:

1. `creator_app.api.create_app()` constructs the base HTTP application.
2. `creator_app.unified_control.install_unified_control()` installs the unified control plane.
3. `creator_app.unified.app` is the resulting ASGI application.
4. `creator_app.unified.main()` is the only supported Python server start function.

No launcher may create a parallel FastAPI app or bypass unified control installation.

## Supported entry points

| Surface | Canonical invocation | Contract |
|---|---|---|
| Local | `./start.sh` | Delegates to `start_unified.sh` |
| Local module | `.venv/bin/python -m creator_app.unified` | Canonical runtime |
| Compatibility | `python3 main.py` | Imports the same `app` and `main` objects |
| Installed CLI | `ck-nexus` | `main:main`, delegated to canonical runtime |
| Docker | `python -m creator_app.unified` | Same runtime module |
| systemd | `python -m creator_app.unified` | Same runtime module |
| Full-system demo | `uvicorn main:app` | Compatibility ASGI object from canonical runtime |

The compatibility interfaces exist to avoid breaking existing operators; they are not separate
runtime implementations.

## Deployment configuration

- `docker-compose.p0.yml` is for isolated P0/staging validation.
- `docker-compose.prod.yml` is the production deployment definition.
- Both build the same `Dockerfile` and therefore run the same canonical application module.
- systemd uses `/etc/cknexus/creator.env` through `EnvironmentFile`; never inline secrets in the
  unit file or repository.
- Compose reads a separately protected environment file with `--env-file`.
- Default application bind is loopback (`127.0.0.1`) for local/systemd. Container bind is
  `0.0.0.0` only inside its container network, behind the configured edge service.

## Authority and evidence boundaries

The unified application surface is not a grant of execution authority. CK-NEXUS Core remains the
policy/state/evidence authority. Workflow engines and external tools remain subordinate execution
planes and cannot approve policy, release, or evidence state.

This contract does not mark any Q10-Q16 gate as passed and does not change `NO-GO` status. Release
promotion still requires complete exact-subject evidence, independent review where required, and
Owner approval.

## Regression invariant

The compatibility module must expose the exact same application and start function objects as
`creator_app.unified`. A regression test enforces this invariant:

```python
import main
from creator_app import unified

assert main.app is unified.app
assert main.main is unified.main
```
