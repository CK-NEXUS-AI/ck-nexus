# RECOVERY_ADDED_FILES

This log records recovery-only material found during Step 2. It is not active CK-NEXUS runtime code.

Total recovery-only files: 185

By source:
- history: 146
- master_system_update: 35
- core_candidate: 4

Largest history groups:
- `EXTRACTED/base44`: 41
- `EXTRACTED/agents`: 40
- `EXTRACTED/CK-NEXUS_CNR-1_CODE_RECONSTRUCTED`: 10
- `EXTRACTED/saifa_v3`: 9
- `EXTRACTED/entities`: 4
- `EXTRACTED/artifacts`: 2
- additional manifests/raw-library items: remaining history files

Master System Update groups:
- `03_Developer_Implementation`: 17
- `04_Evidence`: 6
- `02_Technical_Due_Diligence`: 5
- `01_Client_Safe`: 4
- schema/readme/checksum files: 3

Core candidate recovery-only files:
- 4 files under `ck-nexus/src`

Decision:
- preserve in quarantine candidate only;
- do not activate automatically;
- require Search-first -> Delta-only -> Reuse/Dedup -> Benchmark -> Security Review -> Independent Verification -> Canonical Adoption.

The downloadable Step 2 package contains the exhaustive per-file CSV and quarantined copies with SHA-256 values.
