# CK-NEXUS Launch Operations v1.2

Internal launch-operations package for selling CK-NEXUS Creator Source Edition — Beta.

Purpose: move a qualified buyer from first contact to verified delivery without mixing credentials, production claims, payment data, or mutable source identities.

Product boundary:
- Classification: SELLABLE_SOURCE_BETA
- Production status: NO-GO pending Q10-Q16
- Canonical runtime base: `45fde79c717b09f8675645aa541a5834ebd4f433`
- Frozen runtime subject manifest SHA-256: `51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe`
- Buyer delivery reference: `CK-NEXUS-Creator-Source-Sale-Package-v1.zip`
- Buyer package SHA-256: `1e72d3e6773d4bb9aba46ada2360e4fd3ae94626d9c4b0013e80f0d8f7425907`
- Embedded source ZIP SHA-256: `b77edb4073bbf02b32a745b5b8bae19142539f329c94137f249b43b5ad58c214`
- Buyer package provenance head: `f5cec3186e66e9746f26f208e21e1d75cea990a4`

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
