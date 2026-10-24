# CK-NEXUS AI Evolution Factory V1

Status: IMPLEMENTED / DEVELOPMENT / NOT VERIFIED

## Objective

Turn one human intent into a governed software-engineering improvement loop:

HUMAN INTENT -> RESEARCH -> ARCHITECTURE -> BUILD/PATCH -> TEST -> SECURITY -> BENCHMARK -> INDEPENDENT VERIFICATION -> SCORE -> PROMOTE or REPAIR -> EVIDENCE -> REPEAT

The factory is model-agnostic. GPT, OpenCode, Claude, Gemini, Goose, OpenHands, Ollama, future agents, and future runtimes are interchangeable providers rather than authorities.

## Non-negotiable laws

- NO EVIDENCE -> NO DONE
- SCORE != VERIFIED
- TEST != PRODUCTION
- AI CLAIM != EVIDENCE
- TOOL FAILURE != TASK FAILURE
- BLOCK_PATH != BLOCK_TASK
- Primary-path failure must trigger a bounded alternative-path search.
- Repeated identical failures must change method or escalate.
- Production mutation is always outside the autonomous development loop.

## Factory layers

1. Intent Layer — stores the requested outcome and acceptance criteria.
2. Research Layer — compares current tools, old proven methods, open source, standards and failed approaches.
3. Agent Router — chooses the cheapest capable provider first and escalates only when justified.
4. Execution Boundary — runs code in an isolated disposable workspace.
5. Test Factory — deterministic tests, static checks, dependency audit and regression tests.
6. Security Factory — secret scanning, dependency scanning, static analysis and policy checks.
7. Benchmark Factory — project-specific benchmarks plus external benchmarks where applicable.
8. Verification Layer — independent verifier evaluates artifact and execution evidence.
9. Score Engine — deterministic weighted score; never the sole promotion authority.
10. Evolution Controller — chooses repair, alternative path, rollback or escalation.
11. Evidence Fabric — records source SHA, execution IDs, hashes, provider identity, result and verifier evidence.
12. Release Factory — creates release candidate, documentation, SBOM and sales package only after gates pass.

## Provider routing

Preferred order is capability/cost/evidence based, not a permanent model ranking:

1. Free/local capability when adequate.
2. Existing authenticated subscription through a supported adapter.
3. Low-cost provider.
4. Frontier provider only when benchmark evidence shows material benefit.

The router must record why a provider was selected and whether an alternative was attempted.

## 24-hour operation

GitHub Actions can schedule workflows as frequently as every five minutes, but the factory default is six hours to control cost and noise. The controller is intended to be continuous rather than a single never-ending process.

A later deployment may use scheduled GitHub workflows, event-driven workflows, a self-hosted runner for long-lived local models, or another governed runtime. No design assumes that GitHub Actions itself is a permanent daemon.

## Budget governor

Every AI task has:
- max USD per run
- max USD per day
- max iterations
- max alternative paths
- max parallel agents

If cost is unknown, the task is not silently treated as free.

## Failure handling

FAIL -> CAPTURE -> CLASSIFY -> PRESERVE -> ALTERNATIVE -> RETEST -> VERIFY

Failure classes include provider unavailable, authentication/quota, tool failure, environment failure, dependency failure, test failure, security failure, regression, policy/authorization failure, and verification failure.

Provider failure is BLOCK_PATH unless the task itself is impossible.

## Promotion

Minimum development promotion requires deterministic tests, static/security gates, no unresolved critical regression, and an evidence artifact.

Release candidate additionally requires benchmark evidence, reproducible build, dependency/SBOM evidence, and independent verification.

Production requires separate production evidence and remains NO-GO until those gates exist.

## Current activation state

The deterministic factory preflight and score engine are implemented on the development branch.

The agentic repair layer is intentionally not declared active until:
1. an AI engine is authenticated;
2. the agent workflow is compiled and reviewed;
3. safe outputs are configured;
4. budget limits are enforced;
5. the first real run produces independent evidence.

This prevents a workflow source file from being mistaken for an executing autonomous system.
