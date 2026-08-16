# Buyer Acceptance Checklist

Record PASS/FAIL and evidence for each item.

- [ ] Outer ZIP SHA-256 matches seller sidecar.
- [ ] Internal `SHA256SUMS.txt` verifies.
- [ ] Delivered artifact/version/commit matches the executed commercial schedule.
- [ ] No real seller secret or production customer data is present.
- [ ] `.env.example` can be copied to `.env.local`.
- [ ] Virtual environment installs successfully from the included dependency metadata.
- [ ] `python scripts/release_check.py` completes as documented for the buyer environment, with any external/live prerequisites clearly identified rather than silently passed.
- [ ] Demo Mode starts and `/health` responds.
- [ ] Web UI opens at the documented local address.
- [ ] Buyer can create at least one Demo Mode run and read its history.
- [ ] Buyer has reviewed `KNOWN_LIMITATIONS.md`.
- [ ] Buyer understands third-party accounts/credits/credentials are not transferred by default.
- [ ] Buyer understands this package is not represented as Production Ready.

Acceptance should be signed/recorded against the immutable artifact SHA-256, not against a mutable folder name alone.
