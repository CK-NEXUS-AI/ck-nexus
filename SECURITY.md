# Security Policy

## Supported security scope

Security reports should identify the exact CK-NEXUS commit or artifact being
assessed. Development findings and Production Closure evidence are separate.

## Reporting a vulnerability

Do not post credentials, tokens, private keys, customer data, exploit payloads,
or sensitive infrastructure details in public issues or pull requests.

Preferred reporting path:

1. Use GitHub private vulnerability reporting / Security Advisory if it is
   available for this repository.
2. Otherwise contact the repository owner, `@spinlnw10-art`, through a private
   out-of-band channel.

Include only the minimum information required to reproduce the issue:

- affected commit/tree or release identity;
- affected component/path;
- impact summary;
- bounded reproduction steps;
- logs with secrets redacted;
- suggested mitigation when known.

## CK-NEXUS production boundary

A security report, CI result, scanner output, AI review, or vendor email does
not by itself authorize Q10/Q11/Q12 PASS or Production promotion.

Production closure remains fail-closed and requires the exact canonical
evidence and required independent human approvals.
