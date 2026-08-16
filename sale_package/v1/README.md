# CK-NEXUS Sale Package v1

This directory defines the transaction-safe packaging layer for **CK-NEXUS Creator Source Edition — Beta**.

It intentionally keeps seller/buyer transaction material outside the frozen runtime subject used by prior Q05/Q08 evidence. Runtime code is not modified by this package.

## Package layout

- `buyer/` — documents delivered to the buyer.
- `transaction/` — commercial schedule template to complete before signing.
- `seller/` — seller-only preparation and handover checklist. Do not include private pricing notes in the buyer artifact.
- `RELEASE_IDENTITY.json` — machine-readable immutable source/gate classification.
- `CLAIMS_MATRIX.md` — what may and may not be advertised.
- `seller_tools/build_sale_package_v1.py` — integrity-bound outer package builder.

## Sale classification

`SELLABLE_SOURCE_BETA`

Production Ready remains prohibited until Q10-Q16 are genuinely complete for the same immutable release identity.
