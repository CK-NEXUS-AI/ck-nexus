# Release Status — CK-NEXUS Creator Edition v0.2.0

Decision: **SELLABLE MVP CANDIDATE — NOT FINAL COMMERCIAL RELEASE**

## Passed gates

- Demo Mode end-to-end API smoke path
- 26 automated tests
- Python compilation and Ruff lint
- Bandit source scan
- Dependency vulnerability audit
- Plaintext secret scan
- Security headers, optional access gate, validation, rate limit, and safe text rendering
- Typography-first responsive UI with three themes, command palette, motion reduction, data ticker, output export, and session deletion
- Locked dependency file, Dockerfile, setup scripts, architecture, acceptance, security, and seller documentation
- Built wheel/source archive and installed-wheel Demo API smoke test
- Verified delivery ZIP, internal file checksums, external SHA-256, and runtime-data exclusions
- Codex CLI installed locally and optional Codex Bridge implemented with a safe disabled default,
  fixed workspace, bearer gate, sandbox restriction, timeout, output cap, and secret filtering

## Blocking gates

- Live OpenAI API smoke test `[BLOCKED: usable project-scoped key unavailable]`
- Live Codex Bridge smoke test `[BLOCKED: authenticated Codex state directory is read-only in this build container]`
- Seller identity, price, support, update, refund/acceptance, and jurisdiction fields `[ต้องการข้อมูลเพิ่ม]`
- Final legal and third-party license review `[ต้องการข้อมูลเพิ่ม]`
- Clean-machine test on every operating system promised to buyers `[ต้องการข้อมูลเพิ่ม]`

Do not change the decision to `SELLABLE` until every P0 item in `docs/RELEASE_CHECKLIST.md` is complete.
