# Release Checklist

## P0 — Must pass before sale

- [x] Run `python scripts/release_check.py` successfully. (2026-08-05)
- [x] Run dependency audit from the isolated locked project environment. (2026-08-05)
- [ ] Run one Live Mode smoke test with a valid project-scoped key.
- [x] Confirm no plaintext secret pattern exists in source or release ZIP. (2026-08-05)
- [ ] Replace all `[ต้องการข้อมูลเพิ่ม]` and bracketed commercial-license fields.
- [ ] Confirm third-party licenses and notices with the exact dependency lock.
- [ ] Test installation on the buyer's supported Windows/macOS/Linux version.
- [ ] Set the support window, delivery method, acceptance period, and backup policy.

Packaging evidence: the delivery ZIP excludes local environments, databases, secrets, caches, and VCS metadata; its internal file checksums and external SHA-256 sidecar were verified on 2026-08-05.

## P1 — Strongly recommended

- [ ] Put remote deployments behind HTTPS and a firewall.
- [ ] Generate a high-entropy `CKNEXUS_ACCESS_TOKEN` for remote use.
- [ ] Back up and restore `data/cknexus.db` in a rehearsal.
- [ ] Review model cost/quality on at least 20 representative creator prompts.
- [ ] Add product screenshots and a 3–5 minute onboarding video.

## P2 — Post-MVP roadmap

- [ ] Telegram bot adapter
- [ ] File/document ingestion
- [ ] Content calendar export
- [ ] PostgreSQL and multi-user authentication
- [ ] Background queue, workflow checkpoints, monitoring, and alerts
- [ ] Optional SaaS billing integration

## Release decision

Mark a build `SELLABLE` only when every P0 item is complete. Until the live API, legal, dependency, and clean-machine gates pass, use `SELLABLE MVP CANDIDATE`.
