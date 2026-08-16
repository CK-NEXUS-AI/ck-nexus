# CK-NEXUS Launch Operations v1.2

Internal launch-operations package for selling CK-NEXUS Creator Source Edition — Beta.

Purpose: move a qualified buyer from first contact to verified delivery without mixing credentials, production claims, payment data, or mutable source identities.

Product boundary:
- Classification: SELLABLE_SOURCE_BETA
- Production status: NO-GO pending Q10-Q16
- Canonical runtime base: `45fde79c717b09f8675645aa541a5834ebd4f433`
- Frozen runtime subject manifest SHA-256: `51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe`
- Buyer delivery reference: `CK-NEXUS-Creator-Source-Sale-Package-v1.zip`
- Buyer package SHA-256: `92b9c8dba6b12a3b2588a89031f523caee49101b2fd154f907ca8a4c677d2cfa`

Launch sequence:
1. qualify lead;
2. record buyer requirements;
3. demonstrate Demo Mode and disclosed scope;
4. issue transaction-specific quotation/schedule;
5. receive payment using the seller's approved payment channel outside this repository;
6. verify payment before delivery;
7. record exact package SHA-256 and transaction identity;
8. deliver buyer ZIP only;
9. buyer verifies SHA-256 and performs acceptance checks;
10. record handover/acceptance and start only the support period actually purchased.

Never put API keys, OAuth tokens, bank-account secrets, production data, private keys or buyer passwords in this repository or in the delivery ZIP.
