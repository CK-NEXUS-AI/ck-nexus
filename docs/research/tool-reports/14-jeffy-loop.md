# Tool 14 — Jeffy Loop
Research date: 2026-10-25. Primary source: https://github.com/lenamonj/jeffy-loop.

## 1. Identity
Jeffy Loop is a public GitHub project described as an autonomous audit-and-fix loop for Claude Code. The repository provides a shell Stop hook that feeds the agent its plan, backlog and journal each iteration, and describes machine-checked gates plus an adversarial evaluator. License and exact current version should be confirmed from the repository's LICENSE and release/commit before use; this report does not infer licensing from public visibility alone.

## 2. Category
Self-Optimizing Task Agent workflow. It recursively continues a coding task until explicit gates agree it is done. This is a loop around an existing coding agent, not proof of autonomous model-weight improvement or guaranteed convergence for arbitrary tasks.

## 3. Core Mechanism
The project describes an iteration cycle with audit, attack, verification and proof-like receipts. A shell Stop hook re-injects the plan, backlog and journal so the coding agent continues across iterations. The repository says the engine is in `skills/jeffy/hooks/stop-hook.sh`, the discipline in `skills/jeffy/references/iteration-prompt.txt`, and receipts in `evals/`. It emphasizes judges the loop cannot edit and records every attempt. This creates a more inspectable stopping rule than “the model says it is done,” but correctness still depends on judge quality and what the gates actually test.

## 4. Key Capabilities
- Stop-hook-driven continuation across multiple iterations.
- Structured plan/backlog/journal state.
- Adversarial evaluation and machine-checkable acceptance gates.
- Receipts/artifacts intended to support auditability.
- A public white paper and examples of greenfield builds.

## 5. Evidence
The public repository states that three greenfield builds converged from empty directories, including one with a deliberately mutated specification. These are project-reported demonstrations, not independent benchmarks. The user's requested claims of 132 projects, 103 converged, 56 merged PRs, and involvement by NVIDIA, Meta, Tesla and Apple were not verified from the primary source located in this pass; mark them **No public evidence** until there is a public dataset/receipt table and independent attribution. The closest verifiable proxy is the repository's published code, white paper and per-run receipts.

## 6. Limitations
A loop can consume large amounts of time/tokens or continue chasing a flawed spec. Hooks and shell scripts can fail, be bypassed, or be altered if permissions are not constrained. “Judge cannot edit” must be enforced through filesystem permissions and process boundaries, not merely a prompt. A test suite can be incomplete, and an adversarial evaluator can share the same blind spots as the implementation model. The approach is Claude Code-specific in its current form and not a universal cross-provider orchestrator without adaptation.

## 7. Cost & Access
The repository is publicly accessible; the exact license, install commands and supported version must be read from the current README/LICENSE. The loop itself may be free to inspect, but Claude Code and model inference require a valid subscription or API/provider billing. No evidence supports unlimited free inference. Self-hosting the hook is possible in a local repo, but the model runtime remains provider-dependent unless replaced with a local model.

## 8. Comparison
Compared with Kitchen Loop, Jeffy Loop is a smaller agent-control/continuation pattern with explicit receipts; Kitchen Loop adds a product specification surface, synthetic-user testing and drift control. Compared with FailGate, Jeffy Loop is about continuing through a verified loop, while FailGate's proposed focus is preventing the implementation agent from altering acceptance tests.

## 9. Verdict
A useful pattern to evaluate for bounded engineering tasks where “stop only when evidence is complete” matters. For CK-NEXUS, borrow the receipt model and external stop controller, but put the controller outside the agent's writable workspace, cap iterations/cost, and require independent test/attack results. Do not enable recursive self-modification on production branches.

## Evidence gaps
The requested 132/103/56 metrics and corporate project associations were not verified. Treat the project's own demonstrations as preliminary until reproduced independently.
