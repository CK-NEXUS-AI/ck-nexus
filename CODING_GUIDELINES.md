# CK-NEXUS Coding Guidelines

## 1. Structure

Order modules as imports, constants, types/classes, public functions, helpers, and entrypoint. Keep functions focused and extract deeply nested logic. The configured formatter/linter is authoritative. Python line length is currently 100 characters in `pyproject.toml`.

## 2. Clarity

Use names that explain intent. Comments explain non-obvious constraints, security boundaries, or why a choice exists; they do not narrate obvious syntax. Remove dead code instead of leaving commented-out implementations.

## 3. Input and failure handling

Treat external input, connector output, retrieved content, and tool output as untrusted until policy says otherwise. Validate at boundaries. Fail closed for permission, identity, credential, approval, provenance, and destructive-operation uncertainty. Errors should explain the next safe action without leaking secrets.

## 4. Side effects

Side-effecting work requires explicit capability permission and, when required, approval and idempotency. Retries are bounded. Replays must not duplicate external effects. Production mutation is never inferred from model confidence or administrator reachability.

## 5. Formatting and static checks

- Python: Ruff is the canonical style/lint check.
- JS/TS: use the repository formatter/linter when that package defines one.
- Do not add per-file lint suppressions unless the exception is documented and justified.
- Run `git diff --check` before committing.

## 6. Tests

Every behavior change needs a before/after measurement or a new capability test. Tests must cover the failure path as well as success. Security changes require regression cases proving that bypasses remain denied.

## 7. Documentation

Documentation changes ship with code changes that alter user-visible behavior. Examples must match real commands and current entrypoints. Historical instructions must be visibly marked historical and must not override current runtime truth.

## 8. Review state

Use explicit states such as `DISCOVERED`, `CONNECTED`, `EXECUTED`, `MEASURED_NOT_VERIFIED`, and `VERIFIED`. A development test pass is not independent verification and must not self-promote a candidate to Production.
