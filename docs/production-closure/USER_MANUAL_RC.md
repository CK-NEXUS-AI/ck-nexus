# CK-NEXUS Release Candidate User Manual

Status: Release Candidate documentation. This is not a Production Ready declaration.

## What this release line provides

CK-NEXUS exposes a FastAPI-based creator runtime with agent catalog/runtime services, local run history, provider routing, AGNES runtime surfaces, optional integrations, observability and an email gateway. Availability of optional capabilities depends on environment configuration and credentials.

## Starting the application

Use the installation method documented by the repository and keep the exact `uv.lock` frozen for the release subject. The final production workflow currently treats `python -m creator_app.unified` as the production runtime entrypoint.

Do not copy secrets into configuration files committed to source control. Provider and integration credentials must be supplied through the supported environment/credential-broker paths.

## Authentication

When `CKNEXUS_ACCESS_TOKEN` is configured, protected API requests require an HTTP `Authorization: Bearer <token>` header. The runtime uses constant-time token comparison. Email gateway endpoints use their dedicated webhook-token mechanism when that gateway is enabled.

## API discovery

The application is a FastAPI service and exposes its generated API schema/documentation through the framework's configured documentation surfaces. Treat the running service's OpenAPI schema as the authoritative endpoint catalog for the exact build.

## Optional services

Provider, Gmail, GitHub App, Slack, Google Drive, connector fabric, Codex bridge, AGNES phase-3 controls and email gateway features may be disabled or unavailable when their corresponding settings are not configured. A disabled optional integration must not be interpreted as a runtime failure of unrelated core features.

## Release status

This source can be evaluated or sold as Release Candidate Source Code. Production use must wait for Q10 native Deep Security Scan PASS, Q11 authorized live provider PASS, Q12 delegated cgroup v2 PASS, provenance reconciliation PASS and a successful checksummed Final Production Package.
