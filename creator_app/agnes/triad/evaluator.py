from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from .artifacts import CandidateArtifact, ClaimState


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    candidate_id: str
    evaluator_id: str
    measurement_digest: str
    evidence_refs: tuple[str, ...]
    state: ClaimState


@dataclass(slots=True)
class EvidenceEvaluator:
    evaluator_id: str

    def evaluate(self, candidate: CandidateArtifact, evidence_refs: list[str]) -> EvaluationResult:
        if self.evaluator_id == candidate.producer_id:
            raise ValueError("producer cannot evaluate its own candidate")
        if not evidence_refs:
            raise ValueError("evaluation requires evidence refs")
        canonical = json.dumps(
            {
                "candidate_id": candidate.candidate_id,
                "evaluator_id": self.evaluator_id,
                "evidence_refs": sorted(set(evidence_refs)),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        candidate.attach_measurement(evidence_refs)
        return EvaluationResult(
            candidate_id=candidate.candidate_id,
            evaluator_id=self.evaluator_id,
            measurement_digest=digest,
            evidence_refs=tuple(sorted(set(evidence_refs))),
            state=candidate.state,
        )
