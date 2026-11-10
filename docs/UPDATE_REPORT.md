# CK-NEXUS Update Report

> Generated from the current committed repository snapshot.
> This report summarizes committed evidence; it is not production approval or certification.
> Current release decision remains **NO-GO for Production**.

## Q10–Q16 Gate Status

| Gate | Evidence status | Status index | Evidence source |
|---|---|---:|---|
| Q10 | **STALE** | STALE | evidence/Q10_DEPENDENCY_AUDIT.json |
| Q11 | **STALE** | STALE | evidence/Q11_OPENAI_LIVE.json |
| Q12 | **STALE** | STALE | evidence/Q12_CGROUP_V2.json |
| Q13 | **STALE** | STALE | evidence/Q13_POSTGRES_DR.json |
| Q14 | **STALE** | STALE | evidence/Q14_OBSERVABILITY_ALERT.json |
| Q15 | **STALE** | STALE | evidence/Q15_CLEAN_MACHINE.json |
| Q16 | **STALE** | STALE | evidence/Q16_PRODUCTION_IMAGE.json, evidence/Q16_RUNTIME_LICENSE_SUMMARY.json |

## Summary Badges

| Security | Stability | Release | Delivery |
|---|---|---|---|
| **Security: STALE** | **Stability: STALE** | **Release: STALE** | **Delivery: STALE** |

Status mapping: PASS = 100%; PASS_CANDIDATE = 75%; NOT_STARTED = 0%. FAIL, BLOCKED, NOT_VERIFIED, STALE, and UNKNOWN are shown as status labels, not percentages.
Combined groups are numeric only when every member has a defensible numeric index.

## Recent Commits

| Commit | Date | Subject |
|---|---|---|
| `502f961` | 2026-11-10 | fix: reject stale gate evidence in status badges |
| `d23c37f` | 2026-11-10 | docs: regenerate status artifacts |
| `e08a057` | 2026-11-10 | fix: satisfy strict line length checks |
| `7360835` | 2026-11-10 | ci: validate workflow syntax on pull requests |
| `224c929` | 2026-11-10 | feat: add evidence-driven gate status badges |
| `4d1366c` | 2026-11-05 | feat: unify CK-NEXUS application homepage (#358) |
| `beb5abb` | 2026-11-05 | docs: unify CK-NEXUS homepage (#357) |
| `ebb33a0` | 2026-11-04 | chore(repo): remove superseded docs and stale artifacts (#356) |
| `34d7df4` | 2026-11-04 | fix(runtime): unify all application entrypoints (#353) |
| `6a27e22` | 2026-11-04 | docs(q10): propose auditable open-source security gate (#314) |
| `942ef54` | 2026-11-04 | fix(ci): take published digest from docker push output (#351) |
| `ecfc96b` | 2026-11-04 | chore: pin actions to SHA and record evidence subject (#348) |
| `f4c4447` | 2026-11-01 | feat(channels): add fail-closed multi-channel brain ingress contract (#346) |
| `687d97c` | 2026-11-01 | fix(q16): secure non-root development state storage |
| `b7b6346` | 2026-11-01 | docs: finalize CK-NEXUS GitHub reconciliation report |
| `fa4c029` | 2026-11-01 | feat(brain): add bounded unified cognitive fabric |
| `5805553` | 2026-11-01 | fix(collector): enforce read-only GitHub token |
| `6c093d8` | 2026-10-31 | fix(collector): isolate git config from root system includes (#338) |
| `4a0617e` | 2026-10-31 | feat(dashboard): live read-only development status (#335) |
| `2dc5a29` | 2026-10-31 | docs(release): record current main Q10-Q16 subject drift |

## Authority Boundary

These badges summarize the committed evidence files listed above. They do not change evidence, expected release subjects, gate decisions, Core Authority, or the NO-GO release decision.
