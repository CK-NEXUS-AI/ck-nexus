# Seller Checklist — CK-NEXUS Sale Package v1

## Before quoting

- [ ] Describe product as Creator Source Edition / Beta, not Production Ready.
- [ ] Decide assignment vs perpetual source license.
- [ ] Define support, customization, refund and tax treatment.
- [ ] Obtain legal review for the executed commercial schedule where appropriate.

## Before building

- [ ] Confirm branch descends from canonical runtime base commit `45fde79c...`.
- [ ] Confirm frozen runtime-subject manifest equals `51718986...011fe`.
- [ ] Confirm working tree is clean.
- [ ] Run compile/tests/security/dependency checks available for the exact source.
- [ ] Ensure no `.env.local`, tokens, private keys, production DBs or personal data are present.

## Build and verify

- [ ] `uv build`
- [ ] `python seller_tools/build_sale_package_v1.py`
- [ ] Verify generated outer ZIP and `.sha256` sidecar.
- [ ] Open ZIP and verify buyer docs + source archive + checksums are present.

## Transaction

- [ ] Fill commercial schedule with buyer/seller legal identity.
- [ ] Insert final artifact SHA-256.
- [ ] Record price/payment/tax/support/acceptance terms.
- [ ] Sign/store transaction documents separately from source control.

## Handover

- [ ] Send artifact and checksum through agreed channel.
- [ ] Buyer verifies digest before extraction.
- [ ] Buyer completes acceptance checklist.
- [ ] Never send seller credentials or third-party account secrets.
