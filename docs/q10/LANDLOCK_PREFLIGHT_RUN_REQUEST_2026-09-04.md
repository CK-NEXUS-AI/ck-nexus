# Landlock Preflight Run Request — 2026-09-04

Purpose: trigger a quota-free compatibility measurement using exact OpenAI Codex Security 0.1.24 source and the frozen CK-NEXUS Q10 subject.

Frozen subject:
- commit `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- tree `0525195934f703a8becf8a39f6397b2411e0bb2e`

Scanner:
- source `d4b7d29a87cb86c9072f7905ba867d02385d8fd3`
- package version `0.1.24`

Scope:
- build official upstream `scanner` target
- preserve hardened Docker controls
- test default sandbox and upstream-supported Landlock fallback
- test external-provider CLI configuration through `--dry-run` only

No deep scan, model call, credential, intended quota consumption, Q10 transition, or Production transition is authorized by this request.
