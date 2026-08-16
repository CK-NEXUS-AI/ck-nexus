# Release Status — CK-NEXUS Creator Source Edition Sale Package v1

Decision: **SELLABLE SOURCE/BETA / NO-GO FOR PRODUCTION CLAIMS**

Sale package runtime base:
- Canonical repository: `spinlnw10-art/ck-nexus`
- Canonical main commit: `45fde79c717b09f8675645aa541a5834ebd4f433`
- Canonical main tree: `8bb93b75237ac9891a6c60854f705459dc263921`
- Main commit message records: Production remains NO-GO pending Q10-Q16.

## What may be sold now

This source may be sold as CK-NEXUS Creator Source Edition / Beta / Developer Edition with the documented limitations. It may be demonstrated in Demo Mode and used as a source-code product for buyer evaluation and continued development.

Do **not** market this artifact as Production Ready, Enterprise Production Ready, security-certified, or Q01-Q16 complete.

## Release-gate position

- Q01-Q08: prior evidence exists for source/dependency/CI/live backend closure on the frozen runtime subject.
- Q09: governance binding is merged to canonical main; its evidence record is `PASS_CANDIDATE` and preserves fail-closed authorization semantics.
- Q10: earliest incomplete release gate; genuine Deep Security evidence is still required.
- Q11-Q16: not promoted.

Production status: **NO-GO**.

## Runtime-subject integrity binding

The sale tooling must verify that the frozen runtime subject remains bound to:

`51718986a19e6d11467a9e9e9ab536392b38c59cd674a5f1a7a656632b4011fe`

for the subject paths used by the Q05/Q08 evidence contract:

`creator_app services tests scripts main.py pyproject.toml uv.lock`

If this subject changes, the old Q05/Q08 evidence must be treated as stale and the sale build must fail closed until refreshed.

## Important limitations

- Creator Live Mode still requires buyer-provisioned valid provider credentials.
- Public internet use requires buyer-operated HTTPS/reverse-proxy/access-control hardening.
- Enterprise multi-node, marketplace, customer portal and complete Production Edition qualification are not part of this Sale Package v1.
- Transaction terms, warranty, support, tax, governing law and IP assignment/license selection require a completed commercial schedule and appropriate legal review.
