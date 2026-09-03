# CK-NEXUS Q10 Blocker Substitution Matrix — 2026-09-04

Status: DEVELOPMENT / RESEARCH CONTROL RECORD

This file records tested substitutes so CK-NEXUS does not repeat known dead ends. It does not change Q10, Q11, Q12, Production, verification authority, or the frozen subject.

Frozen Q10 subject:
- commit: `39f5c1adb9d761ab418cf088ff1f051b1ca731d1`
- tree: `0525195934f703a8becf8a39f6397b2411e0bb2e`

Current authority state:
- Q10: `NOT_VERIFIED`
- Q11: `BLOCKED`
- Q12: `BLOCKED`
- Production: `NO-GO / NOT CERTIFIED`

## Decision vocabulary

- `SUBSTITUTE_CONFIRMED` — measured replacement for the specified technical sub-problem.
- `SUBSTITUTE_CANDIDATE` — technically plausible and evidence-backed, but local validation is incomplete.
- `PARTIAL_SUBSTITUTE` — reduces risk/time but cannot satisfy the full original gate.
- `NO_SAFE_SUBSTITUTE` — tested or analyzed alternatives do not preserve the required boundary.
- `AUTHORITY_GATE_CANNOT_BE_SUBSTITUTED` — must remain a designated human/external authority action.

## Matrix

| Blocker | Candidate substitute | State | Evidence / result | Next action |
|---|---|---|---|---|
| Servermall SSH endpoint refuses TCP/22 | Another admitted native Linux host | `SUBSTITUTE_CANDIDATE` | Servermall host remains provisioned but connectivity is not admitted | Keep Servermall remediation open; do not make Q10 depend on it exclusively |
| Native Bubblewrap/user namespace unavailable on GitHub-hosted Ubuntu | Plain GitHub-hosted native bwrap path | `NO_SAFE_SUBSTITUTE` | Run `33799692581`: exact frozen binding PASS, cgroups v2 PASS, Docker sandbox PASS, but `unshare -Ur` and bwrap uid-map failed | Do not repeat this exact native-bwrap probe unless runner image/security policy materially changes |
| Native Bubblewrap/user namespace unavailable | Exact Codex Security 0.1.24 supported legacy Landlock fallback | `SUBSTITUTE_CONFIRMED` for technical sandbox compatibility | Run `33804315546`, job `100811009749`: exact frozen binding PASS; Codex Security 0.1.24; bundled Codex 0.149.1; default bwrap rc=1; Landlock rc=0; compatibility artifact digest `sha256:abf5596fdd9f8c898e6a188ac43bfd68647a668532a2792e7d6b2ec0295aa5a4` | Treat bwrap/userns as no longer the only technical path. Host/evidence authority still requires governance acceptance; do not claim Q10 host admitted from this preflight alone |
| Need a Linux-like host from an existing Windows VPS | WSL2 on Windows Server/VM with nested virtualization | `SUBSTITUTE_CANDIDATE` | Codex supports WSL2 Linux path; CK-NEXUS already has `infra/windows-vps-worker-bootstrap-v1` | Reuse existing Windows worker branch if a suitable host becomes available; verify nested virtualization before admission |
| Dependency-Check cold NVD database timeout | OWASP mirrored NVD datafeed | `SUBSTITUTE_CONFIRMED` for Development | Run `33799837854` completed successfully; 289 dependencies scanned, 0 vulnerabilities, rc=0 | Use mirrored feed for repeatable Development scans; separately decide Q10 evidence policy |
| Need security feedback while canonical Q10 scan is pending | Docker helper farm: Semgrep, Trivy, Checkov, Gitleaks, ShellCheck, Hadolint, Syft, Grype | `PARTIAL_SUBSTITUTE` | Exact canonical Development scans generated isolated artifacts; Syft 178 components, Grype 0 matches | Continue remediation/triage; never promote automatically to Q10 canonical evidence |
| Need SBOM and vulnerability cross-check | Syft + Grype | `SUBSTITUTE_CONFIRMED` for Development cross-check | Run `33798212118` success, artifact digest `sha256:e8fa8efd5b045d3650b82c166d23a49ea3107474a96337909907c2209502ed82` | Keep as parallel SCA evidence; do not claim external certification |
| Codex Security 0.1.24 ChatGPT quota | Exact 0.1.24 `--auth api-key` with `OPENAI_API_KEY`/`CODEX_API_KEY` | `SUBSTITUTE_CANDIDATE` | Exact 0.1.24 documentation supports CI API-key auth; this may use separate API billing/quota | Do not run until Owner explicitly approves any possible paid usage and credential handling |
| Codex Security 0.1.24 ChatGPT quota | Exact 0.1.24 external provider (`openrouter`, `fireworks`, `amazon-bedrock`) | `SUBSTITUTE_CONFIRMED` for CLI/provider plumbing only; `SUBSTITUTE_CANDIDATE` for actual scan authority | Run `33804315546`: exact 0.1.24 OpenRouter dry-run PASS on frozen subject, provider/model parsed successfully, no credential verified and no model request started | Human governance must decide whether provider/model substitution preserves canonical Q10 scan authority; no spend or credentials without approval |
| Codex Security 0.1.24 scanner supply chain | Use 0.1.24 without dependency review | `REVIEW_REQUIRED` | Exact package integrity captured; npm production audit reports 4 vulnerabilities: 1 moderate + 3 high. Affected dependency tree includes `extract-zip` path traversal, `fast-uri` host/SSRF advisories, and `fflate` malformed ZIP64 loop. Some fixes require versions newer than the locked 0.1.24 dependency graph | Triage exploitability in the actual scan path; do not silently upgrade scanner version. Record compensating controls or obtain governance decision before authoritative execution |
| Codex Security authoritative scan requirement | Replace scanner with Semgrep/Trivy/other scanner | `NO_SAFE_SUBSTITUTE` | Other scanners improve coverage but do not reproduce native Codex Security scan semantics/artifacts | Keep them supplemental only |
| Darker/manual verification | ZAP/fuzzing/Nuclei/static analysis preflight | `PARTIAL_SUBSTITUTE` | Automated tools can reduce unknowns but do not equal an explicitly required manual/independent verification authority | Use automation before reviewer handoff, retain manual gate |
| Evidence integrity / reviewer reproducibility | Existing Production Evidence Manifest V2.1 + existing Cosign policy baseline | `SUBSTITUTE_CANDIDATE` for stronger evidence sealing | Existing V2.1 schema already binds commit/tree, artifact SHA-256, evidence-chain hashes, independent verifier fields, JCS payload hash and Ed25519 signature fields. Existing Cosign branch is policy-only and does not execute Cosign | Reuse/dedup existing manifest and Cosign baseline; add an executable fixture-only verification canary before any adoption |
| Independent HUMAN review | AI review / automated reviewer | `AUTHORITY_GATE_CANNOT_BE_SUBSTITUTED` | Separation-of-duties rule | Prepare reviewer pack only; human must decide |
| Owner HUMAN sign-off | AI/automation sign-off | `AUTHORITY_GATE_CANNOT_BE_SUBSTITUTED` | Owner authority rule | Human owner signs final state transition |
| Accredited ISO/other external certification | Internal AI attestation | `AUTHORITY_GATE_CANNOT_BE_SUBSTITUTED` | Certification must come from the relevant external conformity/certification process | Prepare readiness/evidence package; wait for external audit/certification |

## Codex Security 0.1.24 compatibility evidence

Successful compatibility run:
- workflow run: `33804315546`
- compatibility job: `100811009749`
- artifact: `9912290611`
- artifact digest: `sha256:abf5596fdd9f8c898e6a188ac43bfd68647a668532a2792e7d6b2ec0295aa5a4`
- exact package version: `0.1.24`
- npm package integrity: `sha512-14HrUkO9pe3DY6x5JzXSik2/HAoa4T6JcVlY3LK9downpJbgi1yd5qYb5o6jzcj2Dupsc5bpXV6me+Cr9YinHQ==`
- bundled Codex: `codex-cli 0.149.1`
- default Bubblewrap: blocked by hosted-runner network namespace restriction
- supported Landlock fallback: PASS, rc=0
- external provider dry-run: OpenRouter configuration PASS
- deep scan started: NO
- credential used: NO
- intended quota consumption: NO
- authority effect: NONE

Passing this compatibility run does not make GitHub-hosted runners an approved Q10 evidence authority. It only proves that the exact locked scanner has a supported sandbox path on that environment.

## Earlier Landlock preflight history

Attempt 1 used `ghcr.io/openai/codex-security:0.1.24` and failed before sandbox execution because the registry returned `manifest unknown`. This is classified as `IMAGE_TAG_UNAVAILABLE`, not `LANDLOCK_FAILED`.

A later npm-package test initially used the wrong Codex command shape and produced `Failed to execvp linux`; source inspection of OpenAI's exact 0.1.24 `container-ci.yml` corrected the command to `sandbox --enable use_legacy_landlock /usr/bin/true`. The corrected run passed.

## Rules for future substitutes

A substitute is admissible only if it:
1. preserves or strengthens the original security boundary,
2. binds to the exact intended subject,
3. produces attributable and hashable evidence,
4. does not silently change scanner authority/version,
5. does not bypass human authority gates,
6. does not require paid action without explicit Owner approval,
7. is measured before being called confirmed.

Latest exact evidence wins over this document if later measurements differ.
