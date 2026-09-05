# Security Policy

## Supported versions

Security fixes are provided for the current development line and any release explicitly marked as supported. Older snapshots, experiments, and archived candidates are not supported unless a security notice says otherwise.

## Reporting a vulnerability

Do **not** open a public GitHub issue for suspected vulnerabilities, leaked credentials, authentication bypasses, or other sensitive security findings.

Use a private GitHub Security Advisory / private vulnerability reporting channel when available. If that channel is unavailable, contact the repository owner through a private contact method associated with the repository or owner account and include only the minimum information needed to establish contact.

Never paste live secrets, private keys, passwords, tokens, personal data, or exploit payloads into a public issue, pull request, discussion, or CI log.

## Response targets

- Acknowledge a private report within **2 business days**.
- Provide an initial triage/status update within **7 calendar days**.
- High-impact issues are prioritized immediately; remediation timing depends on severity, exploitability, affected versions, and safe validation requirements.
- Reporters receive status updates when material progress or scope changes occur.

These are response targets, not a guarantee of a fixed remediation deadline.

## Triage process

1. Confirm the report through a private channel.
2. Reproduce in an isolated environment without modifying canonical evidence.
3. Classify severity, exploitability, affected components, and exposure.
4. Create a private remediation branch/worktree.
5. Add regression tests and security scans.
6. Require CI plus independent human code review before merge.
7. Release a fix with integrity evidence and, where applicable, a security advisory.
8. Rotate or revoke any exposed credentials separately from source-code remediation.

## Production and verification boundary

Automated scanners, AI agents, CI jobs, badges, machine signatures, and internal evidence do not self-authorize production. CK-NEXUS Q10/Q11/Q12 and production gates remain subject to their separate evidence and human-review requirements.
