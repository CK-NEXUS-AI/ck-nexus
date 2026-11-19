# OMNI Runtime Binding — Development Gate

This module binds OMNI identity, capability lease, pre-execution risk verdict,
tool/target, runtime, verifier, delegation, and evidence requirements before
an execution is admitted to AGNES.

It is intentionally fail-closed. This package does not claim Q10/Q11/Q12 or
production readiness.

Negative-test mapping:
T01 identity, T02 identity proof, T03 capability, T04 scope, T05 expiry,
T06 inactive lease, T07 execution binding, T08 agent binding, T09 policy binding,
T10 risk decision, T11 approval boundary, T12 delegation escalation,
T13 parent execution, T14 tool/target, T15 runtime, T16 verifier,
T17 evidence requirement, T18 production policy handoff.
