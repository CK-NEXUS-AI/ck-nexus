# CK-NEXUS Buyer Acceptance Checklist

Status: BUYER HANDOFF TEMPLATE

## Delivery identity

- [ ] Buyer received the exact delivery ZIP
- [ ] Archive filename matches the executed schedule
- [ ] Archive SHA-256 matches the executed schedule
- [ ] Source commit matches the delivery manifest
- [ ] Source tree matches the delivery manifest

## Integrity and security

- [ ] ZIP integrity test passes
- [ ] Internal SHA256 checksum verification passes
- [ ] No runtime `.env` file is included
- [ ] No API key/token/password is included
- [ ] No SSH/private key is included
- [ ] No production database or personal user data is included
- [ ] Third-party notices are present
- [ ] Full Git bundle is absent unless separately approved and scanned

## Source and documentation

- [ ] Source tree is readable and complete against the delivery manifest
- [ ] Installation/configuration files are present
- [ ] Architecture/system documentation is present
- [ ] Security/governance documentation is present
- [ ] Release status/disclosure is present
- [ ] Build/test instructions are present

## Reproduction

- [ ] Buyer can unpack the archive on a clean machine
- [ ] Dependency installation instructions are usable
- [ ] Build or startup smoke test matches agreed scope
- [ ] Any unsupported environment requirement is disclosed
- [ ] Any external credential required for live integrations is buyer-supplied

## Technical disclosure

Buyer acknowledges the status recorded in the exact delivery package.

Until exact evidence changes, the package must not exceed:
- Q10: NOT_VERIFIED
- Q11: BLOCKED
- Q12: BLOCKED
- Production: NO-GO / NOT CERTIFIED

- [ ] Buyer has read the technical disclosure
- [ ] Buyer understands source-code delivery is distinct from certification
- [ ] Buyer understands third-party services/accounts are separately governed

## Acceptance result

Select one:

- [ ] ACCEPTED
- [ ] ACCEPTED WITH WRITTEN DEFECT LIST
- [ ] REJECTED UNDER AGREED ACCEPTANCE CRITERIA

Defect / exception reference:
[TO BE COMPLETED]

Acceptance date:
[TO BE COMPLETED]

Buyer representative:
[TO BE COMPLETED]

Seller representative:
[TO BE COMPLETED]

This checklist does not replace the executed legal agreement.
