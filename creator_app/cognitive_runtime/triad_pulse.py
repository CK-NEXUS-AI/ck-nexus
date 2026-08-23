from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256

from .triad_evidence import EvidenceEvaluationReceipt, EvidenceVerdict
from .triad_scheduler import TriadRole


class TriadPulseError(ValueError):
    """Raised when the bounded Triad pulse contract is violated."""


class PulseKind(StrEnum):
    REVIEW_15 = "REVIEW_15"
    CONSOLIDATE_20 = "CONSOLIDATE_20"


@dataclass(frozen=True, slots=True)
class TriadPulsePolicy:
    review_every: int = 15
    consolidate_every: int = 20

    def validate(self) -> None:
        if self.review_every < 1:
            raise TriadPulseError("review_interval_invalid")
        if self.consolidate_every < 1:
            raise TriadPulseError("consolidation_interval_invalid")
        if self.review_every == self.consolidate_every:
            raise TriadPulseError("pulse_intervals_must_differ")


@dataclass(frozen=True, slots=True)
class TriadPulseRecord:
    sequence: int
    subject_sha: str
    candidate_id: str
    task_id: str
    verdict: EvidenceVerdict
    score_bps: int
    memory_head_digest: str
    receipt_digest: str
    receipt_json: str
    previous_record_digest: str = ""
    record_digest: str = ""

    def digest_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("record_digest", None)
        return payload

    def recompute_digest(self) -> str:
        raw = json.dumps(
            self.digest_payload(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TriadPulseEvent:
    pulse_id: str
    kind: PulseKind
    subject_sha: str
    ordinal: int
    window_start: int
    window_end: int
    window_size: int
    pulse_ledger_head_digest: str
    window_digest: str
    measured_count: int
    blocked_count: int
    contradicted_count: int
    rejected_count: int
    mean_score_bps: int
    measured_ratio_bps: int
    learning_consolidation_candidate: bool
    verification_ceiling: str = "ADVISORY_ONLY"
    promotion_allowed: bool = False
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
class TriadPulseSnapshot:
    subject_sha: str
    head_digest: str
    records: tuple[TriadPulseRecord, ...]
    pulses: tuple[TriadPulseEvent, ...]


class TriadPulseEngine:
    """Deterministic 15/20 checkpoint pulse over Evidence Evaluator receipts.

    Every accepted evaluator receipt advances one logical ordinal. A review
    pulse is emitted at the 15 cadence and a learning-consolidation candidate
    pulse at the 20 cadence. The engine is advisory only and never promotes a
    candidate, performs an external action, or mutates production state.
    """

    def __init__(
        self,
        subject_sha: str,
        policy: TriadPulsePolicy | None = None,
    ) -> None:
        if not subject_sha.strip():
            raise TriadPulseError("subject_sha_required")
        self.subject_sha = subject_sha
        self.policy = policy or TriadPulsePolicy()
        self.policy.validate()
        self._records: list[TriadPulseRecord] = []
        self._pulses: list[TriadPulseEvent] = []
        self._receipt_digests: set[str] = set()
        self._candidate_receipts: dict[str, str] = {}

    @property
    def head_digest(self) -> str:
        return self._records[-1].record_digest if self._records else ""

    @property
    def records(self) -> tuple[TriadPulseRecord, ...]:
        return tuple(self._records)

    @property
    def pulses(self) -> tuple[TriadPulseEvent, ...]:
        return tuple(self._pulses)

    @staticmethod
    def _require_sha256(value: str, field: str) -> None:
        if len(value) != 64:
            raise TriadPulseError(f"{field}_invalid")
        try:
            int(value, 16)
        except ValueError as exc:
            raise TriadPulseError(f"{field}_invalid") from exc

    @staticmethod
    def _canonical_receipt_json(receipt: EvidenceEvaluationReceipt) -> str:
        return json.dumps(
            asdict(receipt),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    def _validate_receipt(self, receipt: EvidenceEvaluationReceipt) -> None:
        if receipt.subject_sha != self.subject_sha:
            raise TriadPulseError("receipt_subject_mismatch")
        if not receipt.candidate_id.strip() or not receipt.task_id.strip():
            raise TriadPulseError("receipt_identity_missing")
        if receipt.evaluator_role is not TriadRole.EVIDENCE_EVALUATOR:
            raise TriadPulseError("receipt_evaluator_role_invalid")
        if receipt.verification_ceiling != "MEASURED_NOT_VERIFIED":
            raise TriadPulseError("receipt_verification_ceiling_invalid")
        if not receipt.independent_verification_required:
            raise TriadPulseError("receipt_independent_verification_required")
        if receipt.score_bps < 0 or receipt.score_bps > 10_000:
            raise TriadPulseError("receipt_score_invalid")
        self._require_sha256(receipt.candidate_digest, "candidate_digest")
        self._require_sha256(receipt.memory_head_digest, "memory_head_digest")

    @staticmethod
    def _window_digest(records: tuple[TriadPulseRecord, ...]) -> str:
        raw = json.dumps(
            [record.record_digest for record in records],
            separators=(",", ":"),
        )
        return sha256(raw.encode("utf-8")).hexdigest()

    @classmethod
    def _build_event(
        cls,
        *,
        subject_sha: str,
        records: tuple[TriadPulseRecord, ...],
        kind: PulseKind,
        window_size: int,
    ) -> TriadPulseEvent:
        if len(records) < window_size:
            raise TriadPulseError("pulse_window_incomplete")
        window = records[-window_size:]
        measured_count = sum(
            record.verdict is EvidenceVerdict.MEASURED_NOT_VERIFIED
            for record in window
        )
        blocked_count = sum(
            record.verdict is EvidenceVerdict.BLOCKED for record in window
        )
        contradicted_count = sum(
            record.verdict is EvidenceVerdict.CONTRADICTED for record in window
        )
        rejected_count = sum(
            record.verdict is EvidenceVerdict.REJECTED for record in window
        )
        mean_score_bps = sum(record.score_bps for record in window) // window_size
        measured_ratio_bps = measured_count * 10_000 // window_size
        window_digest = cls._window_digest(window)
        ordinal = records[-1].sequence
        raw_id = f"{subject_sha}\0{kind.value}\0{ordinal}\0{window_digest}"
        pulse_id = f"triad-pulse-{sha256(raw_id.encode('utf-8')).hexdigest()}"
        return TriadPulseEvent(
            pulse_id=pulse_id,
            kind=kind,
            subject_sha=subject_sha,
            ordinal=ordinal,
            window_start=window[0].sequence,
            window_end=window[-1].sequence,
            window_size=window_size,
            pulse_ledger_head_digest=records[-1].record_digest,
            window_digest=window_digest,
            measured_count=measured_count,
            blocked_count=blocked_count,
            contradicted_count=contradicted_count,
            rejected_count=rejected_count,
            mean_score_bps=mean_score_bps,
            measured_ratio_bps=measured_ratio_bps,
            learning_consolidation_candidate=(kind is PulseKind.CONSOLIDATE_20),
        )

    def ingest(
        self,
        receipt: EvidenceEvaluationReceipt,
    ) -> tuple[TriadPulseEvent, ...]:
        self._validate_receipt(receipt)
        receipt_json = self._canonical_receipt_json(receipt)
        receipt_digest = sha256(receipt_json.encode("utf-8")).hexdigest()
        if receipt_digest in self._receipt_digests:
            return ()

        existing = self._candidate_receipts.get(receipt.candidate_id)
        if existing is not None and existing != receipt_digest:
            raise TriadPulseError("candidate_receipt_conflict")

        record = TriadPulseRecord(
            sequence=len(self._records) + 1,
            subject_sha=self.subject_sha,
            candidate_id=receipt.candidate_id,
            task_id=receipt.task_id,
            verdict=receipt.verdict,
            score_bps=receipt.score_bps,
            memory_head_digest=receipt.memory_head_digest,
            receipt_digest=receipt_digest,
            receipt_json=receipt_json,
            previous_record_digest=self.head_digest,
        )
        record = replace(record, record_digest=record.recompute_digest())
        self._records.append(record)
        self._receipt_digests.add(receipt_digest)
        self._candidate_receipts[receipt.candidate_id] = receipt_digest

        emitted: list[TriadPulseEvent] = []
        sequence = record.sequence
        if sequence % self.policy.review_every == 0:
            emitted.append(
                self._build_event(
                    subject_sha=self.subject_sha,
                    records=self.records,
                    kind=PulseKind.REVIEW_15,
                    window_size=self.policy.review_every,
                )
            )
        if sequence % self.policy.consolidate_every == 0:
            emitted.append(
                self._build_event(
                    subject_sha=self.subject_sha,
                    records=self.records,
                    kind=PulseKind.CONSOLIDATE_20,
                    window_size=self.policy.consolidate_every,
                )
            )
        self._pulses.extend(emitted)
        return tuple(emitted)

    def snapshot(self) -> TriadPulseSnapshot:
        return TriadPulseSnapshot(
            subject_sha=self.subject_sha,
            head_digest=self.head_digest,
            records=self.records,
            pulses=self.pulses,
        )

    @classmethod
    def verify_snapshot(
        cls,
        snapshot: TriadPulseSnapshot,
        *,
        expected_subject_sha: str,
        expected_head_digest: str,
        policy: TriadPulsePolicy | None = None,
    ) -> None:
        active_policy = policy or TriadPulsePolicy()
        active_policy.validate()
        if snapshot.subject_sha != expected_subject_sha:
            raise TriadPulseError("snapshot_subject_mismatch")
        if snapshot.head_digest != expected_head_digest:
            raise TriadPulseError("snapshot_head_mismatch")

        previous = ""
        seen_receipts: set[str] = set()
        seen_candidates: set[str] = set()
        for expected_sequence, record in enumerate(snapshot.records, start=1):
            if record.sequence != expected_sequence:
                raise TriadPulseError("snapshot_sequence_invalid")
            if record.subject_sha != expected_subject_sha:
                raise TriadPulseError("record_subject_mismatch")
            if record.previous_record_digest != previous:
                raise TriadPulseError("record_chain_broken")
            if record.record_digest != record.recompute_digest():
                raise TriadPulseError("record_digest_mismatch")
            if record.receipt_digest in seen_receipts:
                raise TriadPulseError("duplicate_receipt_digest")
            if record.candidate_id in seen_candidates:
                raise TriadPulseError("duplicate_candidate_receipt")
            cls._require_sha256(record.receipt_digest, "receipt_digest")
            cls._require_sha256(record.memory_head_digest, "memory_head_digest")
            actual_receipt_digest = sha256(record.receipt_json.encode("utf-8")).hexdigest()
            if actual_receipt_digest != record.receipt_digest:
                raise TriadPulseError("receipt_payload_digest_mismatch")
            try:
                payload = json.loads(record.receipt_json)
                payload_verdict = EvidenceVerdict(payload["verdict"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise TriadPulseError("receipt_payload_invalid") from exc
            if payload.get("subject_sha") != record.subject_sha:
                raise TriadPulseError("receipt_payload_subject_mismatch")
            if payload.get("candidate_id") != record.candidate_id:
                raise TriadPulseError("receipt_payload_candidate_mismatch")
            if payload.get("task_id") != record.task_id:
                raise TriadPulseError("receipt_payload_task_mismatch")
            if payload.get("memory_head_digest") != record.memory_head_digest:
                raise TriadPulseError("receipt_payload_memory_head_mismatch")
            if payload_verdict is not record.verdict:
                raise TriadPulseError("receipt_payload_verdict_mismatch")
            if payload.get("score_bps") != record.score_bps:
                raise TriadPulseError("receipt_payload_score_mismatch")
            if payload.get("evaluator_role") != TriadRole.EVIDENCE_EVALUATOR.value:
                raise TriadPulseError("receipt_payload_evaluator_role_invalid")
            if payload.get("verification_ceiling") != "MEASURED_NOT_VERIFIED":
                raise TriadPulseError("receipt_payload_ceiling_invalid")
            if payload.get("independent_verification_required") is not True:
                raise TriadPulseError("receipt_payload_independent_verification_invalid")
            seen_receipts.add(record.receipt_digest)
            seen_candidates.add(record.candidate_id)
            previous = record.record_digest

        calculated_head = snapshot.records[-1].record_digest if snapshot.records else ""
        if calculated_head != snapshot.head_digest:
            raise TriadPulseError("snapshot_head_not_record_head")

        expected_pulses: list[TriadPulseEvent] = []
        for ordinal in range(1, len(snapshot.records) + 1):
            prefix = snapshot.records[:ordinal]
            if ordinal % active_policy.review_every == 0:
                expected_pulses.append(
                    cls._build_event(
                        subject_sha=expected_subject_sha,
                        records=prefix,
                        kind=PulseKind.REVIEW_15,
                        window_size=active_policy.review_every,
                    )
                )
            if ordinal % active_policy.consolidate_every == 0:
                expected_pulses.append(
                    cls._build_event(
                        subject_sha=expected_subject_sha,
                        records=prefix,
                        kind=PulseKind.CONSOLIDATE_20,
                        window_size=active_policy.consolidate_every,
                    )
                )
        if tuple(expected_pulses) != snapshot.pulses:
            raise TriadPulseError("snapshot_pulse_replay_mismatch")
