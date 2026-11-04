# AGNES Voice Persona v1

Status: **post-P0 development only**. This design does not alter Q10/Q11/Q12 or Production NO-GO.

## Core principle

AGNES Voice is not a TTS engine. It is a semantic delivery layer that plans how an already-authorized message should be spoken while preserving a stable AGNES persona.

Pipeline:

`SemanticUtterance -> SpeechContext -> VoicePersonaPlanner -> ProsodyPlan -> Provider Adapter -> Audio -> Voice Verifier -> Evidence`

CK-NEXUS remains the authority for policy, permissions and execution. Voice providers are replaceable renderers.

## Universal Semantic Voice IR

The provider-neutral IR carries:

- exact lexical text
- locale
- intent and importance
- audience role, familiarity, urgency and sensitivity
- selected emotion mode
- speaking rate, pitch intent, energy and pauses
- semantic emphasis targets
- stable AGNES persona identity
- lexical-preservation invariants
- deterministic digest for evidence binding

The planner MUST NOT rewrite text merely to force emotion.

### Thai language invariant

Thai lexical tone is part of word identity. AGNES must preserve correct pronunciation and express emotion through prosody, pacing, energy, pause placement and emphasis. It must not deliberately change lexical tone to create emotion when that can change the word or meaning.

## Emotion modes

v1 defines seven bounded modes:

1. neutral
2. warm
3. serious
4. teaching
5. reassuring
6. urgent
7. celebratory

Modes may change across turns, but the persona baseline remains stable.

## Audience-aware delivery

Audience context can adjust rate, warmth, directness and pause strategy. For example, executive/auditor/operator delivery is slightly more deliberate; familiar contexts may become warmer. This is delivery adaptation, not identity switching.

## Provider mapping

### OpenAI Speech

The adapter maps the plan to `gpt-4o-mini-tts` with `instructions`, a stable voice and bounded speed. Provider instructions are treated as best-effort rendering controls, not verified truth.

### ElevenLabs

The adapter maps the plan to stability, similarity, style and speed controls. Style exaggeration is deliberately conservative because excessive style can reduce stability or pronunciation quality.

## Voice Verifier requirement

TTS output can be non-deterministic. A future verifier must score generated audio before AGNES claims a delivery target was achieved.

Minimum verification dimensions:

- transcript fidelity / word preservation
- Thai pronunciation and lexical-tone correctness
- target emotion match
- speaking-rate deviation
- pause placement around important phrases
- loudness/energy bounds
- persona similarity/consistency
- clipping, artifacts and unexpected non-speech audio
- latency and provider/model identity

A failed verifier result must not be relabeled as success. The planner digest, provider request digest and output-audio digest should be sealed into Evidence.

## Delta-only upgrade rule

A new voice configuration becomes the default only when an evaluation set shows a measurable improvement without violating hard invariants. Suggested release gates:

- lexical fidelity: no regression
- Thai pronunciation: no regression
- persona consistency: no regression
- target emotion preference: statistically better or equal within threshold
- latency/cost: within declared budget
- safety/policy: PASS

## Non-goals for v1

- no claim that AGNES has human feelings
- no automatic production voice deployment
- no cloning of a real person's voice without required consent and governance
- no provider-specific setting is treated as semantic truth
- no mutation of protected production closure evidence
