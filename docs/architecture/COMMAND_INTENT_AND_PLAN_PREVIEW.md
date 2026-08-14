# Command Intent and Plan Preview

Status: architecture contract.

## Goal

A human should state a goal in natural language while CK-NEXUS makes the intended actions inspectable before consequential execution.

## Intent compiler output

The intent compiler produces a typed goal with tenant/session, objective, constraints, requested data sources, output expectations, deadline, budget, privacy/data classification, autonomy ceiling and explicit prohibitions.

Natural-language text is preserved as provenance, but execution uses the typed representation.

## Plan preview

Before high-impact execution, the Control Center can show:

- human-readable objective
- DAG/node list
- semantic capabilities required
- selected/possible implementations
- data that will be read/sent
- expected external mutations
- risk per node
- approvals required
- estimated cost/time
- fallback/compensation paths
- evidence/verifiers required

## Plan hash

A canonicalized executable plan receives a plan hash. Approval binds to this hash or to an explicitly defined envelope that allows only bounded substitutions (for example, swapping between preapproved equivalent read-only providers).

## Material changes

The following invalidate or re-evaluate approval: new external target, higher risk, wider permission, new data classification/region, new side effect, increased cost beyond tolerance, production environment change, or changed policy requirements.

## Ambiguity

If intent ambiguity materially changes side effects or target, CK-NEXUS asks the owner/operator or selects a no-side-effect clarification/research path. It does not guess an irreversible intent.

## Autonomy ceiling

Intent may lower autonomy but cannot raise it above tenant/owner policy. Example: user may say `draft only, do not send`; the plan enforces no external-message capability even if an agent suggests sending.
