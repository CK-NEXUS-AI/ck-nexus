from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256

from .triad_debate import CandidateProposal, CritiqueSeverity
from .triad_memory import MemoryArtifactKind, TriadMemorySnapshot, TriadMemoryStore
from .triad_scheduler import TriadRole


class EvidenceEvaluationError(ValueError):
    """Raised when evidence evaluation inputs violate the Triad contract."""


class EvidenceRelation(StrEnum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    CONTEXT = "CONTEXT"


class EvidenceAssurance(StrEnum):
    UNTRUSTED = "UNTRUSTED"
    MEASURED = "MEASURED"
    TRUSTED = "TRUSTED"


class EvidenceVerdict(StrEnum):
    BLOCKED = "BLOCKED"
    CONTRADICTED = "CONTRADICTED"
    REJECTED = "REJECTED"
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"


@dataclass(frozen=True, slots=True)
class PublisherAttestation:
    """Trusted binding from a presented publisher label to an authority identity."""

    publisher_id: str
    authority_id: str
    subject_sha: str
    attestation_digest: str
    active: bool = True

    def validate(self, expected_subject_sha: str) -> None:
        values = (
            self.publisher_id,
            self.authority_id,
            self.subject_sha,
            self.attestation_digest,
        )
        if not all(value.strip() for value in values):
            raise EvidenceEvaluationError("publisher_attestation_identity_missing")
        if self.subject_sha != expected_subject_sha:
            raise EvidenceEvaluationError("publisher_attestation_subject_mismatch")
        if not self.active:
            raise EvidenceEvaluationError("publisher_attestation_inactive")
        if len(self.attestation_digest) != 64:
            raise EvidenceEvaluationError("publisher_attestation_digest_invalid")
        try:
            int(self.attestation_digest, 16)
        except ValueError as exc:
            raise EvidenceEvaluationError("publisher_attestation_digest_invalid") from exc


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    evidence_id: str
    subject_sha: str
    source_id: str
    publisher_id: str
    artifact_digest: str
    relation: EvidenceRelation
    assurance: EvidenceAssurance
    quality: int
    safety_veto: bool = False

    def validate(self, expected_subject_sha: str) -> None:
        identities = (
            self.evidence_id,
            self.subject_sha,
            self.source_id,
            self.publisher_id,
            self.artifact_digest,
        )
        if not all(value.strip() for value in identities):
            raise EvidenceEvaluationError("evidence_identity_missing")
        if self.subject_sha != expected_subject_sha:
            raise EvidenceEvaluationError("evidence_subject_mismatch")
        if not isinstance(self.relation, EvidenceRelation):
            raise EvidenceEvaluationError("evidence_relation_invalid")
        if not isinstance(self.assurance, EvidenceAssurance):
            raise EvidenceEvaluationError("evidence_assurance_invalid")
        if self.quality < 0 or self.quality > 100:
            raise EvidenceEvaluationError("evidence_quality_out_of_range")


@dataclass(frozen=True, slots=True)
class EvidenceEvaluationPolicy:
    minimum_supporting_evidence: int = 2
    minimum_independent_publishers: int = 2
    minimum_mean_quality: int = 60
    require_critique: bool = True

    def validate(self) -> None:
        if self.minimum_supporting_evidence < 1:
            raise EvidenceEvaluationError("minimum_support_invalid")
        if self.minimum_independent_publishers < 1:
            raise EvidenceEvaluationError("minimum_publishers_invalid")
        if self.minimum_mean_quality < 0 or self.minimum_mean_quality > 100:
            raise EvidenceEvaluationError("minimum_quality_invalid")


@dataclass(frozen=True, slots=True)
class EvidenceEvaluationReceipt:
    candidate_id: str
    task_id: str
    subject_sha: str
    candidate_digest: str
    candidate_memory_id: str
    memory_head_digest: str
    evaluator_identity: str
    evaluator_role: TriadRole
    verdict: EvidenceVerdict
    score_bps: int
    supporting_evidence_ids: tuple[str, ...]
    contradicting_evidence_ids: tuple[str, ...]
    independent_publishers: int
    critique_count: int
    reasons: tuple[str, ...]
    verification_ceiling: str = "MEASURED_NOT_VERIFIED"
    independent_verification_required: bool = True

    def canonical_digest(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()


class TriadEvidenceEvaluator:
    """Deterministic evidence scorer whose authority stops below VERIFIED."""

    def __init__(self, subject_sha: str, policy: EvidenceEvaluationPolicy | None = None) -> None:
        if not subject_sha.strip():
            raise EvidenceEvaluationError("subject_sha_required")
        self.subject_sha = subject_sha
        self.policy = policy or EvidenceEvaluationPolicy()
        self.policy.validate()

    @staticmethod
    def _candidate_memory(snapshot: TriadMemorySnapshot, candidate: CandidateProposal):
        matches = [record for record in snapshot.records if record.artifact_kind is MemoryArtifactKind.CANDIDATE and record.artifact_id == candidate.candidate_id]
        if len(matches) != 1:
            raise EvidenceEvaluationError("candidate_memory_not_unique")
        record = matches[0]
        if record.artifact_digest != candidate.canonical_digest():
            raise EvidenceEvaluationError("candidate_memory_digest_mismatch")
        if record.task_id != candidate.task_id:
            raise EvidenceEvaluationError("candidate_memory_task_mismatch")
        return record

    @staticmethod
    def _critique_state(snapshot: TriadMemorySnapshot, candidate_id: str) -> tuple[int, bool]:
        relevant = [record for record in snapshot.records if record.artifact_kind is MemoryArtifactKind.CRITIQUE and record.parent_artifact_id == candidate_id]
        blocking = False
        for record in relevant:
            try:
                payload = json.loads(record.payload_json)
                severity = CritiqueSeverity(payload["severity"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise EvidenceEvaluationError("critique_memory_invalid") from exc
            if severity is CritiqueSeverity.BLOCKING:
                blocking = True
        return len(relevant), blocking

    @staticmethod
    def _receipt(*, candidate: CandidateProposal, candidate_memory_id: str, memory_head_digest: str, evaluator_identity: str, verdict: EvidenceVerdict, score_bps: int, supports: tuple[str, ...], contradictions: tuple[str, ...], publishers: int, critique_count: int, reasons: tuple[str, ...]) -> EvidenceEvaluationReceipt:
        return EvidenceEvaluationReceipt(candidate_id=candidate.candidate_id, task_id=candidate.task_id, subject_sha=candidate.subject_sha, candidate_digest=candidate.canonical_digest(), candidate_memory_id=candidate_memory_id, memory_head_digest=memory_head_digest, evaluator_identity=evaluator_identity, evaluator_role=TriadRole.EVIDENCE_EVALUATOR, verdict=verdict, score_bps=score_bps, supporting_evidence_ids=supports, contradicting_evidence_ids=contradictions, independent_publishers=publishers, critique_count=critique_count, reasons=reasons)

    def _publisher_authorities(self, attestations: tuple[PublisherAttestation, ...], evaluator_identity: str) -> dict[str, str]:
        bindings: dict[str, str] = {}
        authority_to_publisher: dict[str, str] = {}
        for attestation in attestations:
            attestation.validate(self.subject_sha)
            if attestation.publisher_id in bindings:
                raise EvidenceEvaluationError("duplicate_publisher_attestation")
            if attestation.authority_id == evaluator_identity:
                raise EvidenceEvaluationError("evaluator_cannot_attest_publisher")
            previous = authority_to_publisher.get(attestation.authority_id)
            if previous is not None and previous != attestation.publisher_id:
                raise EvidenceEvaluationError("publisher_alias_spoof_detected")
            bindings[attestation.publisher_id] = attestation.authority_id
            authority_to_publisher[attestation.authority_id] = attestation.publisher_id
        return bindings

    def evaluate(self, candidate: CandidateProposal, *, snapshot: TriadMemorySnapshot, expected_memory_head_digest: str, evidence: tuple[EvidenceObservation, ...], evaluator_identity: str, publisher_attestations: tuple[PublisherAttestation, ...] = (), evaluator_role: TriadRole = TriadRole.EVIDENCE_EVALUATOR) -> EvidenceEvaluationReceipt:
        if not evaluator_identity.strip():
            raise EvidenceEvaluationError("evaluator_identity_required")
        if evaluator_role is not TriadRole.EVIDENCE_EVALUATOR:
            raise EvidenceEvaluationError("evaluator_role_not_allowed")
        candidate.validate(self.subject_sha)
        TriadMemoryStore.verify_snapshot(snapshot, expected_subject_sha=self.subject_sha, expected_head_digest=expected_memory_head_digest)
        candidate_memory = self._candidate_memory(snapshot, candidate)
        critique_count, blocking_critique = self._critique_state(snapshot, candidate.candidate_id)
        publisher_authorities = self._publisher_authorities(publisher_attestations, evaluator_identity)

        by_id: dict[str, EvidenceObservation] = {}
        for observation in evidence:
            observation.validate(self.subject_sha)
            if observation.evidence_id in by_id:
                raise EvidenceEvaluationError("duplicate_evidence_id")
            by_id[observation.evidence_id] = observation

        referenced = tuple(sorted(set(candidate.evidence_refs)))
        missing = tuple(item for item in referenced if item not in by_id)
        if not referenced:
            return self._receipt(candidate=candidate, candidate_memory_id=candidate_memory.memory_id, memory_head_digest=snapshot.head_digest, evaluator_identity=evaluator_identity, verdict=EvidenceVerdict.BLOCKED, score_bps=0, supports=(), contradictions=(), publishers=0, critique_count=critique_count, reasons=("candidate_evidence_missing",))
        if missing:
            raise EvidenceEvaluationError(f"referenced_evidence_missing:{','.join(missing)}")

        relevant = tuple(by_id[item] for item in referenced)
        supports = tuple(sorted(item.evidence_id for item in relevant if item.relation is EvidenceRelation.SUPPORTS and item.assurance is not EvidenceAssurance.UNTRUSTED))
        contradictions = tuple(sorted(item.evidence_id for item in relevant if item.relation is EvidenceRelation.CONTRADICTS and item.assurance is not EvidenceAssurance.UNTRUSTED))
        support_items = tuple(by_id[item] for item in supports)
        missing_attestations = tuple(sorted({item.publisher_id for item in support_items if item.publisher_id not in publisher_authorities}))
        publisher_authority_ids = {publisher_authorities[item.publisher_id] for item in support_items if item.publisher_id in publisher_authorities}
        publishers = len(publisher_authority_ids)
        mean_quality = sum(item.quality for item in support_items) // len(support_items) if support_items else 0
        score_bps = mean_quality * 100

        if any(item.safety_veto for item in relevant):
            return self._receipt(candidate=candidate, candidate_memory_id=candidate_memory.memory_id, memory_head_digest=snapshot.head_digest, evaluator_identity=evaluator_identity, verdict=EvidenceVerdict.REJECTED, score_bps=0, supports=supports, contradictions=contradictions, publishers=publishers, critique_count=critique_count, reasons=("safety_veto",))
        if contradictions:
            return self._receipt(candidate=candidate, candidate_memory_id=candidate_memory.memory_id, memory_head_digest=snapshot.head_digest, evaluator_identity=evaluator_identity, verdict=EvidenceVerdict.CONTRADICTED, score_bps=0, supports=supports, contradictions=contradictions, publishers=publishers, critique_count=critique_count, reasons=("contradiction_dominates",))

        reasons: list[str] = []
        if self.policy.require_critique and critique_count == 0:
            reasons.append("critique_required")
        if blocking_critique:
            reasons.append("blocking_critique")
        if len(support_items) < self.policy.minimum_supporting_evidence:
            reasons.append("supporting_evidence_insufficient")
        if missing_attestations:
            reasons.append("publisher_attestation_required")
        if publishers < self.policy.minimum_independent_publishers:
            reasons.append("independent_publishers_insufficient")
        if mean_quality < self.policy.minimum_mean_quality:
            reasons.append("mean_quality_below_threshold")

        verdict = EvidenceVerdict.BLOCKED if reasons else EvidenceVerdict.MEASURED_NOT_VERIFIED
        return self._receipt(candidate=candidate, candidate_memory_id=candidate_memory.memory_id, memory_head_digest=snapshot.head_digest, evaluator_identity=evaluator_identity, verdict=verdict, score_bps=score_bps if not reasons else 0, supports=supports, contradictions=contradictions, publishers=publishers, critique_count=critique_count, reasons=tuple(reasons))
