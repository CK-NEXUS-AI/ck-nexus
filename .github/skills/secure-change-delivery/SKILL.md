---
name: secure-change-delivery
description: Use before modifying, testing, committing, or pushing CK-NEXUS source code, workflows, configuration, or security-sensitive files.
---

# Secure change delivery

1. Inspect the working tree and remote branch before editing; never overwrite unknown changes.
2. Work in an isolated task branch or worktree.
3. Define the threat/failure model and add regression tests.
4. Run focused tests, lint/format, secret scanning, static security checks, and dependency audit as applicable.
5. Review the final diff for scope, secrets, unintended behavior, and gate bypasses.
6. Commit only intended files. Before pushing, verify the remote branch still equals the expected base; do not force-push.
7. Verify the pushed SHA and CI runs for that SHA.
8. Do not merge or deploy unless separately authorized by the repository's release/governance process.
9. Report implementation, execution, verification, and production status separately.
