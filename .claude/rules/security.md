# Security Rules

- Default deny for unknown or unauthorized actions.
- Least privilege for agents, tools, credentials and runtime identities.
- Secrets are references, never payloads in source or evidence.
- Never print secrets in logs or reports.
- Security gates must fail closed on identity, policy or audit failure.
- Separate dependency, SAST, secret, configuration and deep-review evidence classes.
- Do not claim a security product capability from an unrelated scanner.
