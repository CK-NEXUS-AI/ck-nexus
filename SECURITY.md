# Security Policy

## Supported scope

CK-NEXUS is currently a development-stage project. Security fixes are maintained for:

- the current `main` development branch; and
- release/verification branches explicitly identified as active by the project owner.

Older snapshots and unmaintained branches may not receive fixes. This policy does not imply production certification or external attestation.

## Reporting a vulnerability

Do **not** disclose vulnerability details in a public issue, discussion, pull request, commit message, or CI log.

Maintainers should use a private GitHub Security Advisory draft when that feature is available for the repository. For authorized repository maintainers, the advisory draft page is: https://github.com/spinlnw10-art/ck-nexus/security/advisories/new External reporters should first contact the repository owner through an established private communication channel and share only the minimum information needed to establish a secure reporting path.

If no private reporting channel is available, report only that a private security contact is needed; do not publish exploit details.

## Response targets

These are operational targets, not contractual guarantees:

- acknowledgement: within 3 business days;
- initial triage and status update: within 7 calendar days;
- critical/high-risk remediation target: as soon as practical, normally within 7-14 days;
- medium-risk remediation target: normally within 30 days;
- lower-risk remediation target: normally within 90 days.

## Triage process

1. Confirm the affected component and supported scope.
2. Reproduce the issue in an isolated environment.
3. Classify severity, exploitability, exposure, and affected versions.
4. Create a private remediation branch and evidence record.
5. Run tests and security scans.
6. Require pull-request review before merge.
7. Coordinate disclosure only after a fix or mitigation is available.

## Safe handling

Never include credentials, private keys, authentication tokens, personal data, or live exploit payloads in public reports or CI artifacts.

## Production boundary

A security fix, scan result, badge, Scorecard score, machine signature, or CI success does not by itself authorize production promotion. CK-NEXUS production gates remain fail-closed and require the project-specific independent human review and owner sign-off.
