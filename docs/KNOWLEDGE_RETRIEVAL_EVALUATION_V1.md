# Knowledge Retrieval Evaluation V1

Status: DEVELOPMENT / IMPLEMENTED_NOT_VERIFIED

## Research trigger

Pinterest content research surfaced NVIDIA material around RAG agents, retrieval,
evaluation, agentic systems, NIM microservices, and multimodal AI.

Official NVIDIA material emphasizes:
- evaluating retrieval and generation separately,
- explicit retrieval quality metrics,
- domain-specific knowledge,
- temporal information,
- monitoring and continuous improvement.

Sources checked 2026-09-04:
- https://www.nvidia.com/en-us/on-demand/session/gtc25-dlit71593/
- https://www.nvidia.com/en-us/learn/learning-path/generative-ai-llm/
- https://www.nvidia.com/en-us/learn/certification/agentic-ai-professional/

These sources are research inputs, not CK-NEXUS runtime evidence.

## Search-first decision

Reuse:
- PR #217 Knowledge Lexical Retrieval V1 as the retrieval implementation under test.
- Existing CK-NEXUS observability/evaluation concepts rather than creating a second
  observability authority.
- Existing provenance/freshness filters in Knowledge Fabric/Persistence.

Missing delta:
- a deterministic, provider-independent retrieval-quality benchmark contract that can
  compare the lexical baseline with later retrieval candidates before adoption.

## V1 metrics

- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Hit@K / aggregate hit rate

The evaluator:
- deduplicates repeated retrieved IDs,
- is deterministic,
- requires explicit relevant-claim labels,
- supports an optional as-of field for temporal benchmark datasets,
- compares candidate vs baseline with fail-closed quality thresholds.

## Boundaries

- Retrieval evaluation only; generation-quality evaluation is separate.
- No LLM-as-a-judge is an authority for V1.
- No external provider call.
- No new vector database.
- No automatic canonical adoption.
- No Q10/Q11/Q12 or Production effect.
- Human and independent verification remain required before adoption.

## Intended benchmark flow

Curated cases
-> run current lexical retrieval
-> capture ordered claim IDs
-> compute deterministic metrics
-> run candidate retrieval
-> compute the same metrics
-> compare deltas against declared quality gate
-> security review
-> independent verification
-> human adoption decision
