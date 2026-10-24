# VPS cleanup audit — 2026-10-25

## Observed state
- Root filesystem: 39 GB total, 35 GB used, about 4.4 GB free (89%).
- `/root` totals about 4.7 GB. Notable directories: `.hermes` about 2.1 GB, `.openclaw` about 579 MB, `.config` about 485 MB, `.local` about 432 MB, `.npm` about 352 MB, `.codex` about 181 MB, and `/root/ck-nexus` about 215 MB.
- The CK-NEXUS repo has pre-existing modified and untracked work. No reset, clean, overwrite or unrelated deletion was performed.
- `/tmp` totals about 48 MB and includes browser profiles, live-looking SQLite databases and workflow artifacts; these were not deleted because activity/ownership was not proven.
- Journal usage was observed around 157 MB in the latest detailed check (earlier command showed 78.6 MB; discrepancy means recheck before any log vacuum). Logs were retained as potentially useful operational evidence.
- `/root/.npm/_cacache` was about 2.8 MB; apt archives empty; `/root/.cache` effectively empty. Cache cleaning would not materially recover disk space.

## Decision
No large directory was deleted. The biggest paths may contain OpenClaw/Hermes runtime data, credentials, memory or configuration; deleting them blindly risks breaking services or losing work. Next safe cleanup step is a per-directory inventory with process/service ownership and backup verification, followed by an explicit retention policy. Do not remove `.hermes`, `.openclaw`, `.config`, `.local`, `.codex`, `.venv`, databases or browser profiles solely because they are large.

## External archive
Dropbox is connected under an account, but no folder was created because the connector requires a separately confirmed exact mutation plan. Proposed target: `/CK-NEXUS-Research-Archive/` with research reports, synthesis, workflow policy and a manifest; no secrets, environment files, logs or private email data. User confirmation is required before creating the folder and uploading files.
