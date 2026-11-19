# MERGE_CONFLICT_NOTES

Step 2 found 26 recovery files that map to an existing canonical path but have different content.

Decision for all 26 conflicts:
- canonical GitHub version wins;
- recovery version is preserved only in the downloadable quarantine candidate using `.recovered.<source>.<ext>` naming;
- no canonical file is overwritten;
- no recovery conflict is activated as runtime code.

Conflict sources:
- history package: 24
- core candidate: 2

Important mapped conflict families include:
- historical Sprint 1 billing files vs canonical `services/billing/*` and `tests/test_billing.py`;
- reconstructed CNR-1 architecture/runtime files vs canonical files with corresponding paths;
- reconstructed `.env.example` / architecture documentation where mapped paths already exist;
- tiny external core candidate `main.py` and `pyproject.toml` vs canonical project files.

Five additional recovery files were byte-identical to canonical content and were skipped rather than duplicated.

The exhaustive conflict list, source path, canonical path, canonical SHA-256 and recovery SHA-256 are stored in `reports/RECOVERY_COMPARISON.csv` and `reports/MERGE_CONFLICT_NOTES.md` in the Step 2 downloadable package.
