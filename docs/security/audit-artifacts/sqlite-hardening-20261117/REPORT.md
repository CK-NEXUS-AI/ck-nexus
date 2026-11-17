# SQLite Hardening Evidence

Branch: `integration/termux-change-sync-policy-20261117`
Base: `f7b64885df118cc81183aedce202a5068291d841`

- Pytest: 1,016 passed, 2 skipped (61.79s)
- Ruff, format, diff check: PASS
- Bandit: 0 high / 0 medium / 0 low
- pip-audit: 0 known vulnerabilities; 1 local package not auditable from PyPI
- SQLite quick_check: `ok`; service `active`
- DB directory/file modes: `0700` / `0600`

## SHA-256

- `creator_app/sqlite_security.py` — `d61d21395bde2cf797cbdb6cbb191a1401834d752489a74b385ce6d3e78ddec7`
- `creator_app/brain/journal.py` — `d4080464c2555c26ae64a9a29279a0f9938b3aad69f19c6c8276f4a602136be5`
- `creator_app/global_knowledge/ebook_store.py` — `183dc0519366cc980b87bec14c0358492a70d1418d1f2b516368b6dc15a94a2e`
- `tests/test_brain_runtime.py` — `642856004fab24c080da08c715b6c61000610823d4bf84820d6ffb008483acdf`
- `tests/capability_fabric/test_ebook_store.py` — `333633dd9425ed35a5fb944456a31d4ca872dd0fe3d23b052554a750b241fb4a`

- Codex independent review: no actionable findings; acceptable for PR within POSIX and same-UID trust boundaries.

## Limitations

Codex reviewed the five-file snapshot only, not the full repository. Race windows and symlinked journal/SHM sidecars are not directly tested. This evidence does not certify production readiness or close Q10–Q16. No merge or deployment.
