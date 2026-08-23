from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256

from .triad_pulse import (
    PulseKind,
    TriadPulseEngine,
    TriadPulseEvent,
    TriadPulseSnapshot,
)


class LearningConsolidationError(ValueError):
    """Raised when learning consolidation violates provenance or safety."""


class LearningDecision(StrEnum):
    PROPOSE = "PROPOSE"
    BLOCK = "BLOCK"
    QUARANTINE = "QUARANTINE"


@dataclass(frozen=True, slots=True)
class LearningConsolidationPolicy:
    minimum_measured_ratio_bps: int = 7500
    minimum_mean_score_bps: int = 6000
    maximum_contradicted: int = 0
    maximum_rejected: int = 0

    def validate(self) -> None:
        bounded = (
            self.minimum_measured_ratio_bps,
            self.minimum_mean_score_bps,
        )
        if any(value < 0 or value > 10_000 for value in bounded):
            raise LearningConsolidationError("learning_threshold_out_of_range")
        if self.maximum_contradicted < 0 or self.maximum_rejected < 0:
            raise LearningConsolidationError("learning_negative_limit_invalid")


@dataclass(frozen=True, slots=True)
class LearningCandidate:
    learning_id: str
    subject_sha: str
    capability: str
    insight: str
    expected_delta: str
    semantic_fingerprint: str
    source_pulse_id: str
    source_pulse_digest: str
    source_window_digest: str
    source_receipt_digests: tuple[str, ...]
    measured_ratio_bps: int
    mean_score_bps: int
    verification_ceiling: str = "MEASURED_NOT_VERIFIED"
    independent_verification_required: bool = True
    experiment_required: bool = True
    adoption_allowed: bool = False
    auto_activation_allowed: bool = False
    external_action_allowed: bool = False
    production_mutation_allowed: bool = False

    def canonical_digest(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LearningConsolidationResult:
    decision: LearningDecision
    subject_sha: str
    source_pulse_id: str
    candidate: LearningCandidate | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LearningLedgerRecord:
    sequence: int
    subject_sha: str
    learning_id: str
    candidate_digest: str
    semantic_fingerprint: str
    source_pulse_id: str
    supersedes_learning_id: str = ""
    previous_record_digest: str = ""
    record_digest: str = ""

    def recompute_digest(self) -> str:
        payload = asdict(self)
        payload.pop("record_digest", None)
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class LearningLedgerSnapshot:
    subject_sha: str
    head_digest: str
    records: tuple[LearningLedgerRecord, ...]


class TriadLearningConsolidator:
    """Turns a valid 20-pulse into an evidence-bound learning candidate.

    The output is proposal-only. It can feed a later experiment/verification
    stage but cannot install, activate, adopt, execute, or promote a capability.
    """

    def __init__(
        self,
        subject_sha: str,
        policy: LearningConsolidationPolicy | None = None,
    ) -> None:
        if not subject_sha.strip():
            raise LearningConsolidationError("subject_sha_required")
        self.subject_sha = subject_sha
        self.policy = policy or LearningConsolidationPolicy()
        self.policy.validate()
        self._ledger: list[LearningLedgerRecord] = []
        self._by_learning_id: dict[str, LearningLedgerRecord] = {}
        self._by_fingerprint: dict[str, LearningLedgerRecord] = {}

    @property
    def ledger_head_digest(self) -> str:
        return self._ledger[-1].record_digest if self._ledger else ""

    @staticmethod
    def _normalize(value: str, field: str) -> str:
        normalized = " ".join(value.strip().split()).casefold()
        if not normalized:
            raise LearningConsolidationError(f"{field}_required")
        return normalized

    @classmethod
    def semantic_fingerprint(
        cls,
        capability: str,
        insight: str,
        expected_delta: str,
    ) -> str:
        payload = {
            "capability": cls._normalize(capability, "capability"),
            "insight": cls._normalize(insight, "insight"),
            "expected_delta": cls._normalize(expected_delta, "expected_delta"),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _find_pulse(
        snapshot: TriadPulseSnapshot,
        pulse_id: str,
    ) -> TriadPulseEvent:
        matches = [pulse for pulse in snapshot.pulses if pulse.pulse_id == pulse_id]
        if len(matches) != 1:
            raise LearningConsolidationError("source_pulse_not_unique")
        return matches[0]

    @staticmethod
    def _window_receipt_digests(
        snapshot: TriadPulseSnapshot,
        pulse: TriadPulseEvent,
    ) -> tuple[str, ...]:
        records = tuple(
            record
            for record in snapshot.records
            if pulse.window_start <= record.sequence <= pulse.window_end
        )
        if len(records) != pulse.window_size:
            raise LearningConsolidationError("source_window_incomplete")
        return tuple(record.receipt_digest for record in records)

    def consolidate(
        self,
        *,
        snapshot: TriadPulseSnapshot,
        expected_pulse_head_digest: str,
        source_pulse_id: str,
        capability: str,
        insight: str,
        expected_delta: str,
        known_fingerprints: tuple[str, ...] = (),
        conflicting_fingerprints: tuple[str, ...] = (),
        supersedes_learning_id: str = "",
    ) -> LearningConsolidationResult:
        TriadPulseEngine.verify_snapshot(
            snapshot,
            expected_subject_sha=self.subject_sha,
            expected_head_digest=expected_pulse_head_digest,
        )
        pulse = self._find_pulse(snapshot, source_pulse_id)
        if pulse.kind is not PulseKind.CONSOLIDATE_20:
            raise LearningConsolidationError("source_pulse_not_consolidation")
        if not pulse.learning_consolidation_candidate:
            raise LearningConsolidationError("source_pulse_not_learning_candidate")
        if pulse.subject_sha != self.subject_sha:
            raise LearningConsolidationError("source_pulse_subject_mismatch")
        if pulse.promotion_allowed or pulse.external_action_allowed:
            raise LearningConsolidationError("source_pulse_authority_exceeded")
        if pulse.production_mutation_allowed:
            raise LearningConsolidationError("source_pulse_production_authority_exceeded")

        fingerprint = self.semantic_fingerprint(capability, insight, expected_delta)
        known = set(known_fingerprints)
        known.update(self._by_fingerprint)
        conflicts = set(conflicting_fingerprints)

        if fingerprint in conflicts:
            return LearningConsolidationResult(
                decision=LearningDecision.QUARANTINE,
                subject_sha=self.subject_sha,
                source_pulse_id=pulse.pulse_id,
                candidate=None,
                reasons=("semantic_conflict",),
            )
        if fingerprint in known:
            return LearningConsolidationResult(
                decision=LearningDecision.BLOCK,
                subject_sha=self.subject_sha,
                source_pulse_id=pulse.pulse_id,
                candidate=None,
                reasons=("duplicate_learning_delta",),
            )

        quarantine_reasons: list[str] = []
        if pulse.contradicted_count > self.policy.maximum_contradicted:
            quarantine_reasons.append("contradiction_limit_exceeded")
        if pulse.rejected_count > self.policy.maximum_rejected:
            quarantine_reasons.append("rejection_limit_exceeded")
        if quarantine_reasons:
            return LearningConsolidationResult(
                decision=LearningDecision.QUARANTINE,
                subject_sha=self.subject_sha,
                source_pulse_id=pulse.pulse_id,
                candidate=None,
                reasons=tuple(quarantine_reasons),
            )

        block_reasons: list[str] = []
        if pulse.measured_ratio_bps < self.policy.minimum_measured_ratio_bps:
            block_reasons.append("measured_ratio_below_threshold")
        if pulse.mean_score_bps < self.policy.minimum_mean_score_bps:
            block_reasons.append("mean_score_below_threshold")
        if block_reasons:
            return LearningConsolidationResult(
                decision=LearningDecision.BLOCK,
                subject_sha=self.subject_sha,
                source_pulse_id=pulse.pulse_id,
                candidate=None,
                reasons=tuple(block_reasons),
            )

        if supersedes_learning_id:
            previous = self._by_learning_id.get(supersedes_learning_id)
            if previous is None:
                raise LearningConsolidationError("superseded_learning_missing")
            if previous.semantic_fingerprint == fingerprint:
                raise LearningConsolidationError("supersession_requires_new_delta")

        receipt_digests = self._window_receipt_digests(snapshot, pulse)
        pulse_digest = pulse.canonical_digest()
        raw_id = f"{self.subject_sha}\0{fingerprint}\0{pulse_digest}"
        learning_id = f"triad-learning-{sha256(raw_id.encode('utf-8')).hexdigest()}"
        candidate = LearningCandidate(
            learning_id=learning_id,
            subject_sha=self.subject_sha,
            capability=" ".join(capability.strip().split()),
            insight=" ".join(insight.strip().split()),
            expected_delta=" ".join(expected_delta.strip().split()),
            semantic_fingerprint=fingerprint,
            source_pulse_id=pulse.pulse_id,
            source_pulse_digest=pulse_digest,
            source_window_digest=pulse.window_digest,
            source_receipt_digests=receipt_digests,
            measured_ratio_bps=pulse.measured_ratio_bps,
            mean_score_bps=pulse.mean_score_bps,
        )
        candidate_digest = candidate.canonical_digest()
        existing = self._by_learning_id.get(learning_id)
        if existing is not None:
            if existing.candidate_digest != candidate_digest:
                raise LearningConsolidationError("learning_identity_conflict")
            return LearningConsolidationResult(
                decision=LearningDecision.PROPOSE,
                subject_sha=self.subject_sha,
                source_pulse_id=pulse.pulse_id,
                candidate=candidate,
                reasons=("idempotent_existing_candidate",),
            )

        record = LearningLedgerRecord(
            sequence=len(self._ledger) + 1,
            subject_sha=self.subject_sha,
            learning_id=learning_id,
            candidate_digest=candidate_digest,
            semantic_fingerprint=fingerprint,
            source_pulse_id=pulse.pulse_id,
            supersedes_learning_id=supersedes_learning_id,
            previous_record_digest=self.ledger_head_digest,
        )
        record = replace(record, record_digest=record.recompute_digest())
        self._ledger.append(record)
        self._by_learning_id[learning_id] = record
        self._by_fingerprint[fingerprint] = record
        return LearningConsolidationResult(
            decision=LearningDecision.PROPOSE,
            subject_sha=self.subject_sha,
            source_pulse_id=pulse.pulse_id,
            candidate=candidate,
            reasons=("experiment_and_independent_verification_required",),
        )

    def ledger_snapshot(self) -> LearningLedgerSnapshot:
        return LearningLedgerSnapshot(
            subject_sha=self.subject_sha,
            head_digest=self.ledger_head_digest,
            records=tuple(self._ledger),
        )

    @staticmethod
    def verify_ledger_snapshot(
        snapshot: LearningLedgerSnapshot,
        *,
        expected_subject_sha: str,
        expected_head_digest: str,
    ) -> None:
        if snapshot.subject_sha != expected_subject_sha:
            raise LearningConsolidationError("ledger_subject_mismatch")
        if snapshot.head_digest != expected_head_digest:
            raise LearningConsolidationError("ledger_head_mismatch")
        previous = ""
        seen_ids: set[str] = set()
        seen_fingerprints: set[str] = set()
        for sequence, record in enumerate(snapshot.records, start=1):
            if record.sequence != sequence:
                raise LearningConsolidationError("ledger_sequence_invalid")
            if record.subject_sha != expected_subject_sha:
                raise LearningConsolidationError("ledger_record_subject_mismatch")
            if record.previous_record_digest != previous:
                raise LearningConsolidationError("ledger_chain_broken")
            if record.record_digest != record.recompute_digest():
                raise LearningConsolidationError("ledger_record_digest_mismatch")
            if record.learning_id in seen_ids:
                raise LearningConsolidationError("duplicate_learning_id")
            if record.semantic_fingerprint in seen_fingerprints:
                raise LearningConsolidationError("duplicate_learning_fingerprint")
            if record.supersedes_learning_id and record.supersedes_learning_id not in seen_ids:
                raise LearningConsolidationError("supersession_not_prior")
            seen_ids.add(record.learning_id)
            seen_fingerprints.add(record.semantic_fingerprint)
            previous = record.record_digest
        calculated_head = snapshot.records[-1].record_digest if snapshot.records else ""
        if calculated_head != snapshot.head_digest:
            raise LearningConsolidationError("ledger_head_not_record_head")
