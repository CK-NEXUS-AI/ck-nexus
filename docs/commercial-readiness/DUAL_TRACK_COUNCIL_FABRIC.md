# CK-NEXUS Dual-Track Council Fabric

Status: POST-P0 DEVELOPMENT ONLY
Authority boundary: CK-NEXUS remains the sole authority for state, policy, permissions, execution promotion and evidence interpretation.

## Objective
Run two complementary capability-development systems in parallel while preventing experimental work from silently becoming production authority.

## Track A — Governed Core Evolution
Purpose: evolve canonical CK-NEXUS with conservative, evidence-producing changes.

Roles:
- Architect — defines contracts, boundaries and acceptance criteria.
- Builder — implements an isolated change set.
- Updater — reconciles the proposal against the latest canonical main and relevant standards/dependencies.
- Verifier — independently validates functional, security, provenance and evidence requirements.
- Red Team — challenges assumptions and adds adversarial/failure cases.

Promotion rule: the Builder cannot independently verify or approve its own change. Verifier or Red Team vetoes are explicit evidence and cannot be discarded without a new proposal revision.

## Track B — Experimental Capability Lab
Purpose: search broadly for capabilities, patterns, open-source projects, standards, tools and implementation strategies that CK-NEXUS does not yet have.

Roles:
- Researcher — gathers candidates and source evidence.
- Scout — checks whether the capability already exists in canonical source or another Post-P0 branch.
- Prototype Builder — produces bounded experimental code or design artifacts.
- Evaluator — measures quality, cost, performance, interoperability and supply-chain risk.
- Challenger — argues against adoption and identifies hidden complexity, lock-in and security/privacy/compliance risk.

Lab outputs are RESEARCH_ONLY or LOCAL_EVALUATE until they pass the Track A promotion contract.

## Debate Loop
Every capability proposal uses the same loop:

1. GAP_DISCOVERED
2. RESEARCH_PACKET_CREATED
3. ARCHITECT_POSITION
4. CHALLENGER_POSITION
5. BUILDER_FEASIBILITY
6. VERIFIER_REQUIREMENTS
7. COUNCIL_DEBATE
8. DECISION
9. IMPLEMENTATION_OR_REJECTION
10. TEST_AND_ATTACK
11. INDEPENDENT_VERIFICATION
12. EVIDENCE_PERSISTED
13. PROMOTION_REVIEW

## Structured Debate Artifact
Each debate must record:
- proposal_id
- capability_id
- exact base commit
- exact base tree
- problem statement
- candidate approaches
- source references
- researcher findings
- architect recommendation
- builder feasibility
- updater drift/dependency assessment
- verifier objections
- red-team/challenger objections
- security impact
- privacy impact
- compliance impact
- cost impact
- operational complexity
- duplication assessment
- required tests
- unresolved questions
- final decision
- evidence identities/digests

Allowed decisions:
- REJECT
- RESEARCH_ONLY
- LOCAL_EVALUATE
- IMPLEMENT_POST_P0
- ELIGIBLE_FOR_PROMOTION_REVIEW

No debate artifact can set PRODUCTION_READY.

## Conversation / Chat Model
The user-facing chat may render a council transcript, but the durable system-of-record is the structured debate artifact plus source/test/evidence identities. Chat prose is advisory and never authoritative by itself.

Suggested conversational sequence:

Researcher: What exists externally and what evidence supports it?
Architect: How would it fit CK-NEXUS without creating a second authority?
Builder: What is the minimum implementation slice?
Updater: What changed in main, dependencies, standards or providers?
Challenger: Why should we not build this?
Verifier: What exact tests/evidence are required to trust it?
Governor: Choose the next bounded state transition.

## Scheduling Model
The roles can operate as separate recurring lanes:
- Research lane — discovers new candidates.
- Design lane — converts candidates into contracts.
- Build lane — implements approved Post-P0 slices.
- Update lane — reconciles latest source/standards/provider changes.
- Verify lane — independently tests and persists evidence.
- Red-team lane — attacks assumptions and implementations.

The lanes communicate through proposal IDs and evidence IDs, not through mutable shared chat state alone.

## Capability Agenda
Initial source: Issue #91.

Priority waves:
1. capability gap discovery and evidence automation
2. coverage intelligence and E2E
3. SBOM/supply-chain provenance
4. performance/load/stress/soak
5. continuous verification and autonomous remediation
6. multi-verifier consensus and digital twin
7. chaos/failure injection
8. model quality/cost and provider reliability
9. memory integrity and evidence graph
10. compliance/incident/commercial evidence
11. plugin/MCP trust intelligence
12. autonomous capability builder

## GitHub Helper Policy
External GitHub repositories may be used as research/input only after:
- source identity is recorded
- license is checked
- repository/publisher provenance is recorded
- relevant commit/tag is pinned
- dependency/supply-chain risk is assessed
- copied code is not introduced without license/provenance review
- unknown code is evaluated in sandbox/quarantine

A GitHub repository or agent framework is never an authority merely because it is popular or available.

## Safety Boundary
- no PR #14 merge
- no Q10/Q11/Q12 promotion
- no production deployment
- no raw credential persistence
- no self-approval
- no silent veto suppression
- experimental evidence cannot substitute for production evidence
