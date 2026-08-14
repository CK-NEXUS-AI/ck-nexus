# Model and Cognitive Worker Evaluation Scorecard

Status: architecture contract.

## Goal

Routing quality improves from measured task performance, not vendor reputation or a single global leaderboard.

## Evaluation dimensions

Depending on task class:

- contract/structured-output correctness;
- task success/quality;
- factual grounding and citation quality;
- code/test correctness;
- reasoning consistency where externally verifiable;
- safety/policy adherence;
- tool-call proposal correctness;
- instruction hierarchy/prompt-injection resilience;
- latency;
- measured/estimated cost;
- context utilization;
- multilingual/domain performance;
- refusal/abstention calibration;
- historical regression rate.

## Task-class profiles

Scores are segmented by semantic capability, language/domain, modality and relevant context-size band. A worker excellent at coding is not automatically preferred for research or creative tasks.

## Evidence levels

`UNMEASURED`, `SYNTHETIC_EVAL`, `SHADOW_OBSERVED`, `CANARY_OBSERVED`, `PRODUCTION_OBSERVED`.

Higher evidence level does not override current policy/health/data restrictions.

## Statistics

Store sample count, evaluation window, confidence/uncertainty, distribution/percentiles where useful, dataset/version, evaluator identity and contamination/limitations notes. Small samples cannot produce falsely precise rankings.

## Regression

A model/provider/version change creates a new observation series or versioned implementation identity. Material regressions automatically reduce eligibility/score or trigger shadow/canary revalidation according to policy.

## Human quality feedback

User/operator feedback may inform evaluation but is tenant-scoped and abuse-resistant. Explicit preference is distinct from factual correctness.

## No self-certification

A model cannot validate its own capability merely by claiming it. Evaluation uses independent tests/verifiers or externally observable task outcomes.
