# CK-NEXUS Buyer Delivery V2 Specification

Status: DEVELOPMENT / BUYER-PACKAGING CANDIDATE

Base commit:
`b4146db8e23dff49520cbbc9d0194a15bcc5872d`

This specification converts the requested full-source delivery structure into
a truthful package built from the actual tracked CK-NEXUS repository.

## Governing rules

1. Never claim Production Ready, Q10 VERIFIED, Q11 PASS, Q12 PASS, or external
   certification unless exact evidence supports that claim.
2. Only tracked repository files are copied into the source package by
   default. Untracked local files are excluded.
3. Real `.env` files, credentials, private keys, databases, logs, caches,
   and local runtime state are excluded.
4. A full Git bundle is NOT included by default because repository history can
   contain secrets that are absent from the current tree.
5. Legal documents remain templates until transaction-specific legal review
   and signatures are complete.
6. Third-party components remain governed by upstream licenses.
7. The package must contain internal file SHA-256 checksums plus an external
   archive SHA-256 sidecar.

## Requested structure mapped to real CK-NEXUS assets

| Requested area | Buyer package area | Source |
| --- | --- | --- |
| Legal / transfer documents | `00-LEGAL/` | `COMMERCIAL_LICENSE_TEMPLATE.md` plus legal-review warning |
| System overview | `01-SYSTEM-DOCS/` | README, release status, delivery manifest, release checklist |
| Full source code | `02-SOURCE-CODE/repository/` | sanitized tracked repository tree |
| Security / verification | `03-SECURITY-AND-VERIFICATION/` | tracked security, privacy, AGNES, audit and evidence-related code/docs |
| Automation / CI / ops | `04-AUTOMATION-AND-OPS/` | workflows and scripts |
| Interfaces | `05-INTERFACES/` | web UI, gateway, integrations |
| Developer documentation | `06-DEVELOPER-DOCS/` | tracked docs and Markdown documentation |
| Install / config | `07-INSTALL-AND-CONFIG/` | Docker/Compose/env example/lock/install entry points |
| Evidence / checksums | root + security/docs areas | generated SHA256 and tracked evidence that is safe to distribute |
| Assets / licenses | `09-ASSETS-AND-LICENSES/` | third-party notices and safe tracked assets |
| Git reference | `10-GIT-REFERENCE/` | commit history text, branch summary, exact commit/tree; no bundle by default |

## Current mandatory disclosure

At package-generation time the delivery metadata must state:

- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

This does not prevent a source-code sale. It prevents a false Production Ready
or certification claim.

## Git-history transfer policy

`git-bundled-repo.bundle` is intentionally omitted from V2.

Before adding a full bundle:

1. run a dedicated full-history secret scan;
2. review every historical secret finding;
3. rotate any credential that ever appeared in history;
4. confirm third-party or private material may legally be transferred;
5. record the scan result and reviewer;
6. obtain seller approval for the exact bundle hash.

Until then, transfer:
- current source package;
- exact commit/tree reference;
- textual commit history;
- branch summary.

## Legal package policy

The repository may include transaction templates, but not executed legal
documents. The final sale package must be completed outside automated source
generation with:
- legal party names;
- transaction type: assignment or license;
- price and payment terms;
- governing law;
- tax terms;
- acceptance period;
- support/warranty terms;
- exact artifact SHA-256;
- signatures.

The generated package must never imply that an unsigned template is an
executed contract.

## Build

```bash
python scripts/package_buyer_delivery.py \
  --version v0.2.0-buyer-candidate \
  --output-directory dist/buyer-delivery
```

Expected outputs:

```text
CK-NEXUS-FULL-SOURCE-DELIVERY-v0.2.0-buyer-candidate.zip
CK-NEXUS-FULL-SOURCE-DELIVERY-v0.2.0-buyer-candidate.zip.sha256
```

## Validation before buyer handoff

Required:
- source exact commit/tree recorded;
- current-tree secret scan PASS;
- buyer packager secret scan PASS;
- ZIP integrity PASS;
- internal SHA256 file verification PASS;
- forbidden private/runtime file check PASS;
- third-party notices present;
- clean-machine install smoke test recorded;
- transaction documents legally reviewed;
- buyer acceptance window defined.

Latest exact evidence wins.
