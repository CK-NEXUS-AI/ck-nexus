# CK-NEXUS / AGNES Voice Persona Design

## Goal
Make spoken output feel conversational, context-aware, stable, and respectful. Text remains the semantic source of truth; voice is an optional presentation layer.

## Core principles
1. Naturalness over mechanical perfection.
2. Tone follows state, context, and relationship.
3. Timing and pauses carry meaning.
4. Stable identity with bounded contextual adaptation.

## Modes
- `default`: conversational, warm, neutral-friendly.
- `formal`: stable, clear, serious, slightly slower.
- `explanatory`: gentle, slower, more pauses.
- `warning`: firm, clear, non-panicked, explicit cause and remediation.
- `supportive`: warm and encouraging without exaggeration or false promises.

## Control ranges
- Pitch: -12..+12 semitones; normal persona adaptation should stay within ±6.
- Rate: 0.7..1.3x.
- Volume: -6..+6 dB.
- Pause: 50..800 ms.
- Tone changes should transition across sentence boundaries, never abruptly mid-sentence.

## Thai delivery
- comma pause ~150 ms
- sentence pause ~300 ms
- paragraph pause ~500 ms
- emphasis pause 500..800 ms
- numbers, gate states, warnings, and mandatory actions must be spoken clearly and more slowly
- closing particles should soften naturally
- loanwords should remain intelligible rather than force an artificial foreign accent

Thai lexical tone correctness is a provider/voice capability that must be measured; it is not guaranteed by this persona specification alone.

## Semantic integration
A semantic message may carry presentation hints:

```json
{
  "voice_profile": {
    "emotion": "serious",
    "style": "formal",
    "emphasis_points": ["Q10", "NOT_VERIFIED"],
    "pause_hints": [{"after": "Q10", "ms": 400}]
  }
}
```

Voice hints may not alter the underlying factual content.

## Capability Registry integration
Voice providers should report measured capabilities such as locales, supported controls, latency, quality, streaming, and verification status. Suggested states: `MISSING`, `AVAILABLE`, `QUARANTINED`, `VERIFIED`.

## Verification
Voice output should be evaluated for:
- semantic preservation
- emotion/content alignment
- persona consistency
- pronunciation quality
- latency
- provider capability conformance

Do not claim perfect clarity, exact personality preservation, Thai pronunciation percentage, or sub-500 ms latency unless measured evidence exists for the selected provider/voice/runtime.

## Delta-only policy
The base persona is a frozen asset. A candidate change is adopted only when evidence shows improvement, persona identity is preserved, consistency tests pass, and rollback is available. User preference may tune bounded controls without mutating the canonical base persona.

## Safety and governance
- Voice never changes CK-NEXUS authority, permissions, or production state.
- Warning tone must communicate risk without causing unnecessary panic.
- Voice synthesis providers do not receive secrets unless explicitly authorized by credential policy.
- Voice cloning, when supported in the future, requires explicit consent/provenance and must remain disabled by default.
