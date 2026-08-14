# Evidence Freshness and Provenance

Status: architecture contract. This does not establish Q15 PASS.

## Evidence subject

Every release/gate evidence artifact names the exact subject it proves: commit SHA/tree, manifest digest, image/artifact digest, environment identity, configuration/policy hash and relevant dependency lock digest.

Evidence for one subject cannot be silently reused for a changed subject unless the gate explicitly proves subject-equivalence and records how.

## Freshness

Each evidence type defines maximum acceptable age and invalidation triggers. Freshness fields include produced_at, observed_at where distinct, valid_until or freshness policy, and invalidated_by references.

Examples of invalidation triggers:

- source tree/manifest changes;
- dependency lock changes;
- policy/security configuration changes;
- staging environment replacement;
- credential/permission changes affecting the tested path;
- provider/runtime version changes when material;
- recovery/observability configuration changes.

## Provenance

Evidence records producer identity/version, method/toolchain, command/protocol profile where reproducible, input subject digests, environment, output/result, limitations and parent evidence refs.

## Result taxonomy

Use `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, `INSUFFICIENT_EVIDENCE`, and `STALE`. Never collapse unsupported/not-run into PASS. A successful CI job can still contain a blocked gate, and a failed CI job can reflect correct fail-closed evidence behavior rather than a software regression.

## External/live evidence

Live binding, alert delivery, restore drills and provider/API checks record external target identity in redacted form, observation timestamp, expected condition, actual result and operator/verifier receipt. Static source alone cannot replace required live evidence.

## Release bundle

Q15 release evidence bundle should be generated only after prerequisite gates are complete and should contain a manifest of evidence artifacts, digests, gate mapping, freshness evaluation and final subject. Stale historical release status files must not be rewritten to imply newer PASS state without supporting artifacts.
