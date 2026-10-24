# CK-NEXUS Unified Package

This package preserves the canonical CK-NEXUS source and adds a compact control surface without replacing the existing detailed demo.

## Run

```bash
./start_unified.sh
```

Open `http://127.0.0.1:8000/control` for the main-heading control surface. The existing detailed demo remains at `/demo` and OpenAPI remains at `/docs`.

## Control model

The control surface uses eight main groups: AI & Creator Core, AGNES Skills & Automation, Development Council & OpenCode, Integration & Connector Network, Email & Communication, Data/Memory/Knowledge, Governance & Security, and Operations & Commerce.

Subfunctions are discovered from the actual FastAPI runtime routes and shown only after a main group is expanded. Existing domain security boundaries remain authoritative; the control layer does not proxy arbitrary calls or bypass credentials, approvals, policy, sandbox, or execution governance.

## Package authority

The release workflow packages the entire branch while excluding only `.git` and generated `dist` output. It emits a SHA-256 checksum beside the ZIP.
