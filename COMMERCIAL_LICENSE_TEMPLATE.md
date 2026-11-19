# CK-NEXUS Source Code License / Assignment Template

Status: transaction template. Complete the commercial schedule and obtain appropriate legal review before signing.

## 1. Parties

The seller and buyer are the legal entities identified in the executed commercial schedule attached to this agreement.

## 2. Software

“Software” means the CK-NEXUS source package, documentation, tests, build scripts and specifically identified release artifacts delivered under the executed schedule. Third-party software remains governed by its own license.

## 3. Transaction model

The executed schedule must select exactly one model:

- source-code assignment / outright transfer of the seller-owned deliverables; or
- perpetual source license with the rights expressly stated in the schedule.

No rights in third-party accounts, API credits, cloud subscriptions, domains, credentials, customer data or secrets are transferred unless the schedule expressly says so.

## 4. Delivery identity

The schedule must record the exact CK-NEXUS version, Git commit, artifact SHA-256, delivery date and included files. Acceptance is measured against that immutable delivery identity and the acceptance criteria supplied with the release.

## 5. Credentials and personal data

The delivery must not contain API keys, OAuth tokens, passwords, private keys, production databases or personal customer data. The buyer provisions its own runtime credentials after delivery.

## 6. Third-party components

Third-party components are not relicensed by the seller. `THIRD_PARTY_NOTICES.md`, the dependency lock and applicable upstream license terms form part of the delivery record.

## 7. Warranty, support and liability

Warranty period, defect-remediation scope, support channel, response targets, exclusions and liability terms are defined only by the executed commercial schedule. This repository template does not create those obligations by itself.

## 8. Security and production readiness

A release may be described as Production Ready only when its release gate records all required production/staging checks as PASS for the same immutable commit and artifact. Development Candidate or NO-GO artifacts must not be represented as Production Ready.

## 9. Signatures

Signatures, legal names, addresses, governing law, effective date, price, taxes and payment terms belong in the transaction-specific executed schedule maintained outside the source repository.
