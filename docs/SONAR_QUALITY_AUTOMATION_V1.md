# CK-NEXUS Sonar Quality Automation V1

Status: DEVELOPMENT / SAFE TO REVIEW  
Production effect: NONE  
Q10 authority effect: NONE

## Purpose

This development slice adds reproducible SonarQube Cloud analysis, quality-gate evidence,
developer remediation reporting, buyer/executive summaries, secret-leak checks, and continuous
GitHub Actions integration for CK-NEXUS.

The known SonarQube Cloud project identity is:

- organization: `spinlnw10-art`
- project key: `spinlnw10-art_ck-nexus-pro-evolution`

A second Sonar project key has not been established from the available evidence. Do not guess it.
The runner accepts an explicit project key argument so the second project can be added without
changing the security model once its exact identity is known.

## Credential boundary

The Sonar token previously exposed in chat must be revoked and replaced.

This repository never stores a token. Live analysis requires:

- VPS: `SONAR_TOKEN` in the process environment only.
- GitHub Actions: repository secret `SONAR_TOKEN`.

Do not put Sonar credentials in:

- `sonar-project.properties`
- source code
- workflow command-line parameters
- report artifacts
- shell history
- documentation

## Quality policy

`config/sonar/quality_policy_v1.json` defines an internal CK-NEXUS engineering policy.

New code target:

- Security rating A
- Reliability rating A
- Maintainability rating A
- Coverage >= 80%
- Duplication <= 3%
- No blocker/critical issues
- Security hotspots reviewed

Overall-code minimum target:

- Security rating B or better
- Reliability rating B or better
- Maintainability rating B or better
- No blocker/critical issues

The policy is informed by Sonar quality/security practice, OWASP Top 10, and CISQ/ISO 5055
quality concerns. It is not ISO/CISQ certification.

## VPS analysis

The VPS-installed SonarScanner CLI is version `8.1.0.6389`.

Official archive SHA-256 verified on 2026-09-04:

`bb8f709f9cb73352f8d1260a3b3c506c0f41146754bc630762c126d795499d0b`

Run:

```bash
read -s SONAR_TOKEN
export SONAR_TOKEN
scripts/sonar/run_ci_analysis.sh spinlnw10-art_ck-nexus-pro-evolution
unset SONAR_TOKEN
```

The script binds each run to the exact Git commit/tree, waits for the Sonar quality gate,
collects API results, generates reports, scans reports for accidental credential material,
and hashes all generated evidence.

## Generated evidence

Each successful run produces a timestamped directory with:

- `run-metadata.txt`
- `sonar-scanner.log`
- `sonar-analysis.json`
- `DEVELOPER_REPORT.md`
- `EXECUTIVE_BUYER_SUMMARY.md`
- `SHA256SUMS.txt`

## Continuous analysis

`.github/workflows/sonar-quality.yml` runs on pull requests, pushes to `main`, and manual
dispatch.

It performs a local configuration/security preflight even when no secret exists.
Live Sonar analysis executes only when GitHub secret `SONAR_TOKEN` exists.

On `main`, a missing Sonar token is an explicit configuration failure.

## Merge-control limitation

A failing Sonar workflow provides a status check, but blocking a manual merge also requires
GitHub branch protection/ruleset configuration that marks the check as required. Repository
plan/permission capability must be verified before claiming merge blocking is enforced.

## Remediation order

1. Security blocker/critical issues.
2. Critical reliability issues.
3. Unreviewed security hotspots.
4. Test coverage gaps.
5. Major maintainability issues.
6. Duplication and lower-severity debt.

After every remediation batch, rerun the exact analysis on the new commit and compare the new
report against the previous signed/hash-bound evidence.

## Evidence and sales boundary

Sonar reports may be included in technical due diligence or buyer handover packages as automated
engineering evidence. They must be labeled as automated tool results and must not be presented as
formal certification, an independent audit, Q10 verification, or Production approval.
