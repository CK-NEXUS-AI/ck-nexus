# CK-NEXUS Tool + VPS Docker Helper Operating Policy

Status: DEVELOPMENT POLICY CANDIDATE  
Authority effect: NONE  
Production effect: NONE

## Standing directive

For CK-NEXUS work, use all **materially relevant** available tools rather than
limiting work to a single connector or execution surface.

A Docker/VPS helper lane is a mandatory attempt on each substantive engineering,
research, benchmark, security, or verification task when the authorized VPS is
available.

This policy does not require random or redundant tool calls. A tool is used only
when it materially improves speed, evidence, independence, or coverage.

## Mandatory execution pattern

1. Search first for existing implementation and evidence.
2. Inspect exact GitHub branch/SHA/tree where relevant.
3. Attempt the authorized VPS Docker helper lane.
4. Assign bounded helper roles as useful:
   - architecture/dedup review
   - implementation review
   - tests/benchmark
   - security review
   - evidence consistency
5. Compare helper output with GitHub CI and canonical evidence.
6. Preserve disagreements rather than forcing consensus.
7. Stage only reversible Development changes.
8. Keep human authority gates unchanged.

## VPS helper safety boundary

Default helper execution is:
- read-only source mount where practical,
- non-root container user where practical,
- no host Docker socket unless specifically required and reviewed,
- no raw credentials in prompts, logs, artifacts, or evidence,
- bounded CPU/RAM/time,
- no Production deployment,
- no merge,
- no Q10/Q11/Q12 authority mutation,
- no self-approval.

Helpers are advisory and are never Independent Human Reviewers.

## Availability rule

If the VPS/helper connector is unavailable:
- record the exact availability blocker,
- do not claim the helper ran,
- continue with safe GitHub/Linux CI or other available evidence lanes,
- retry the VPS helper lane when connectivity returns.

Tool unavailability does not authorize weakening a gate.

## Evidence minimum

Record where applicable:
- task/purpose,
- exact subject SHA/tree,
- helper role,
- Docker image/version/digest,
- command or entrypoint,
- started/finished timestamp,
- exit code,
- raw artifact reference,
- artifact SHA-256,
- resource limits,
- security result,
- authority effect.

## Governance

SEARCH_FIRST -> DELTA_ONLY -> REUSE/DEDUP -> BENCHMARK ->
SECURITY_REVIEW -> INDEPENDENT_VERIFICATION -> CANONICAL_ADOPTION

No helper, AI agent, ChatGPT instance, CI workflow, or Docker container may act as
the Independent Human Reviewer or Owner final sign-off.
