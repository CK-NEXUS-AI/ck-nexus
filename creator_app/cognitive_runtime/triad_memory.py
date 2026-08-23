from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256
from typing import Any

from .triad_debate import (
    CandidateCritique,
    CandidateProposal,
    CandidateStatus,
    CritiqueSeverity,
    DebateRound,
)
from .triad_scheduler import TriadRole


class TriadMemoryError(ValueError):
    """Raised when Triad memory integrity or provenance is invalid."""


class MemoryArtifactKind(StrEnum):
    CANDIDATE = "CANDIDATE"
    CRITIQUE = "CRITIQUE"
    ROUND = "ROUND"


@dataclass(frozen=True, slots=True)
class TriadMemoryRecord:
    sequence: int
    memory_id: str
    subject_sha: str
    task_id: str
    round_id: str
    artifact_kind: MemoryArtifactKind
    artifact_id: str
    artifact_digest: str
    payload_digest: str
    correlation_id: str
    causation_memory_id: str = ""
    supersedes_memory_id: str = ""
    parent_artifact_id: str = ""
    revision: int = 0
    payload_json: str = ""
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
class TriadMemorySnapshot:
    subject_sha: str
    head_digest: str
    records: tuple[TriadMemoryRecord, ...]


class TriadMemoryStore:
    """Append-only exact-subject memory for explicit Triad debate artifacts.

    Only public candidate, critique, and debate-round artifacts are retained.
    Hidden chain-of-thought is neither defined nor stored by this contract.
    """

    def __init__(self, subject_sha: str, *, max_records: int = 10_000) -> None:
        if not subject_sha.strip():
            raise TriadMemoryError("subject_sha_required")
        if max_records < 1:
            raise TriadMemoryError("max_records_invalid")
        self.subject_sha = subject_sha
        self.max_records = max_records
        self._records: list[TriadMemoryRecord] = []
        self._by_memory_id: dict[str, TriadMemoryRecord] = {}
        self._by_artifact: dict[
            tuple[MemoryArtifactKind, str], TriadMemoryRecord
        ] = {}

    @property
    def head_digest(self) -> str:
        return self._records[-1].record_digest if self._records else ""

    @property
    def records(self) -> tuple[TriadMemoryRecord, ...]:
        return tuple(self._records)

    @staticmethod
    def _canonical_payload(value: object) -> str:
        if isinstance(value, DebateRound):
            payload: dict[str, object] = {
                "round_id": value.round_id,
                "task_id": value.task_id,
                "subject_sha": value.subject_sha,
                "candidates": [
                    asdict(item)
                    for item in sorted(
                        value.candidates,
                        key=lambda item: item.candidate_id,
                    )
                ],
                "critiques": [
                    asdict(item)
                    for item in sorted(
                        value.critiques,
                        key=lambda item: item.critique_id,
                    )
                ],
            }
        else:
            payload = asdict(value)  # type: ignore[arg-type]
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

    @staticmethod
    def _payload_digest(payload_json: str) -> str:
        return sha256(payload_json.encode("utf-8")).hexdigest()

    @staticmethod
    def _memory_id(
        kind: MemoryArtifactKind,
        artifact_id: str,
        artifact_digest: str,
    ) -> str:
        raw = f"{kind.value}\0{artifact_id}\0{artifact_digest}"
        return f"triad-mem-{sha256(raw.encode('utf-8')).hexdigest()}"

    @staticmethod
    def _load_mapping(payload_json: str) -> dict[str, Any]:
        try:
            payload = json.loads(payload_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise TriadMemoryError("artifact_payload_json_invalid") from exc
        if not isinstance(payload, dict):
            raise TriadMemoryError("artifact_payload_must_be_object")
        return payload

    @staticmethod
    def _candidate_from_mapping(payload: dict[str, Any]) -> CandidateProposal:
        try:
            candidate = CandidateProposal(
                candidate_id=str(payload["candidate_id"]),
                task_id=str(payload["task_id"]),
                subject_sha=str(payload["subject_sha"]),
                proposer_role=TriadRole(payload["proposer_role"]),
                statement=str(payload["statement"]),
                rationale=str(payload["rationale"]),
                expected_delta=str(payload["expected_delta"]),
                assumptions=tuple(
                    str(item) for item in payload.get("assumptions", ())
                ),
                evidence_refs=tuple(
                    str(item) for item in payload.get("evidence_refs", ())
                ),
                parent_candidate_id=str(
                    payload.get("parent_candidate_id", "")
                ),
                revision=int(payload.get("revision", 1)),
                status=CandidateStatus(
                    payload.get("status", CandidateStatus.PROPOSED)
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TriadMemoryError("candidate_payload_invalid") from exc
        candidate.validate(candidate.subject_sha)
        return candidate

    @staticmethod
    def _critique_from_mapping(payload: dict[str, Any]) -> CandidateCritique:
        try:
            critique = CandidateCritique(
                critique_id=str(payload["critique_id"]),
                candidate_id=str(payload["candidate_id"]),
                task_id=str(payload["task_id"]),
                subject_sha=str(payload["subject_sha"]),
                critic_role=TriadRole(payload["critic_role"]),
                severity=CritiqueSeverity(payload["severity"]),
                findings=tuple(
                    str(item) for item in payload.get("findings", ())
                ),
                counter_evidence_refs=tuple(
                    str(item)
                    for item in payload.get("counter_evidence_refs", ())
                ),
                requested_changes=tuple(
                    str(item)
                    for item in payload.get("requested_changes", ())
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TriadMemoryError("critique_payload_invalid") from exc
        critique.validate(critique.subject_sha)
        return critique

    @classmethod
    def _round_from_mapping(cls, payload: dict[str, Any]) -> DebateRound:
        try:
            candidates_raw = payload["candidates"]
            critiques_raw = payload.get("critiques", [])
            if not isinstance(candidates_raw, list):
                raise TypeError("candidates must be a list")
            if not isinstance(critiques_raw, list):
                raise TypeError("critiques must be a list")
            if any(not isinstance(item, dict) for item in candidates_raw):
                raise TypeError("candidate payload must be an object")
            if any(not isinstance(item, dict) for item in critiques_raw):
                raise TypeError("critique payload must be an object")
            debate_round = DebateRound(
                round_id=str(payload["round_id"]),
                task_id=str(payload["task_id"]),
                subject_sha=str(payload["subject_sha"]),
                candidates=tuple(
                    cls._candidate_from_mapping(item)
                    for item in candidates_raw
                ),
                critiques=tuple(
                    cls._critique_from_mapping(item)
                    for item in critiques_raw
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TriadMemoryError("round_payload_invalid") from exc
        debate_round.validate()
        return debate_round

    @classmethod
    def _artifact_from_payload(
        cls,
        kind: MemoryArtifactKind,
        payload_json: str,
    ) -> CandidateProposal | CandidateCritique | DebateRound:
        payload = cls._load_mapping(payload_json)
        if kind is MemoryArtifactKind.CANDIDATE:
            return cls._candidate_from_mapping(payload)
        if kind is MemoryArtifactKind.CRITIQUE:
            return cls._critique_from_mapping(payload)
        if kind is MemoryArtifactKind.ROUND:
            return cls._round_from_mapping(payload)
        raise TriadMemoryError("artifact_kind_invalid")

    @classmethod
    def _artifact_digest_from_payload(
        cls,
        kind: MemoryArtifactKind,
        payload_json: str,
    ) -> str:
        artifact = cls._artifact_from_payload(kind, payload_json)
        return artifact.canonical_digest()

    @classmethod
    def _validate_payload_binding(cls, record: TriadMemoryRecord) -> None:
        artifact = cls._artifact_from_payload(
            record.artifact_kind,
            record.payload_json,
        )
        if artifact.subject_sha != record.subject_sha:
            raise TriadMemoryError("artifact_subject_binding_mismatch")
        if artifact.task_id != record.task_id:
            raise TriadMemoryError("artifact_task_binding_mismatch")

        if isinstance(artifact, CandidateProposal):
            if artifact.candidate_id != record.artifact_id:
                raise TriadMemoryError("candidate_id_binding_mismatch")
            if artifact.revision != record.revision:
                raise TriadMemoryError("candidate_revision_binding_mismatch")
            if artifact.parent_candidate_id != record.parent_artifact_id:
                raise TriadMemoryError("candidate_parent_binding_mismatch")
        elif isinstance(artifact, CandidateCritique):
            if artifact.critique_id != record.artifact_id:
                raise TriadMemoryError("critique_id_binding_mismatch")
            if artifact.candidate_id != record.parent_artifact_id:
                raise TriadMemoryError("critique_target_binding_mismatch")
            if record.revision != 0 or record.supersedes_memory_id:
                raise TriadMemoryError("critique_memory_shape_invalid")
        else:
            if artifact.round_id != record.round_id:
                raise TriadMemoryError("round_id_binding_mismatch")
            if artifact.round_id != record.artifact_id:
                raise TriadMemoryError("round_artifact_id_mismatch")
            if record.revision != 0:
                raise TriadMemoryError("round_revision_invalid")
            if record.causation_memory_id or record.supersedes_memory_id:
                raise TriadMemoryError("round_memory_link_invalid")
            if record.parent_artifact_id:
                raise TriadMemoryError("round_parent_artifact_invalid")

    def _append(
        self,
        *,
        task_id: str,
        round_id: str,
        artifact_kind: MemoryArtifactKind,
        artifact_id: str,
        artifact_digest: str,
        payload_json: str,
        correlation_id: str,
        causation_memory_id: str = "",
        supersedes_memory_id: str = "",
        parent_artifact_id: str = "",
        revision: int = 0,
    ) -> TriadMemoryRecord:
        identities = (
            task_id.strip(),
            round_id.strip(),
            artifact_id.strip(),
            correlation_id.strip(),
        )
        if not all(identities):
            raise TriadMemoryError("memory_identity_missing")
        if not artifact_digest.strip():
            raise TriadMemoryError("artifact_digest_required")
        if revision < 0:
            raise TriadMemoryError("revision_invalid")
        calculated = self._artifact_digest_from_payload(
            artifact_kind,
            payload_json,
        )
        if calculated != artifact_digest:
            raise TriadMemoryError("artifact_payload_digest_mismatch")

        key = (artifact_kind, artifact_id)
        existing = self._by_artifact.get(key)
        if existing is not None:
            if existing.artifact_digest != artifact_digest:
                raise TriadMemoryError(
                    f"artifact_identity_conflict:{artifact_id}"
                )
            return existing
        if len(self._records) >= self.max_records:
            raise TriadMemoryError("memory_capacity_exceeded")

        links = (
            (causation_memory_id, "causation_memory_missing"),
            (supersedes_memory_id, "superseded_memory_missing"),
        )
        for linked_id, error in links:
            if linked_id and linked_id not in self._by_memory_id:
                raise TriadMemoryError(f"{error}:{linked_id}")

        memory_id = self._memory_id(
            artifact_kind,
            artifact_id,
            artifact_digest,
        )
        if memory_id in self._by_memory_id:
            raise TriadMemoryError(f"memory_id_conflict:{memory_id}")

        record = TriadMemoryRecord(
            sequence=len(self._records) + 1,
            memory_id=memory_id,
            subject_sha=self.subject_sha,
            task_id=task_id,
            round_id=round_id,
            artifact_kind=artifact_kind,
            artifact_id=artifact_id,
            artifact_digest=artifact_digest,
            payload_digest=self._payload_digest(payload_json),
            correlation_id=correlation_id,
            causation_memory_id=causation_memory_id,
            supersedes_memory_id=supersedes_memory_id,
            parent_artifact_id=parent_artifact_id,
            revision=revision,
            payload_json=payload_json,
            previous_record_digest=self.head_digest,
        )
        self._validate_payload_binding(record)
        record = replace(
            record,
            record_digest=record.recompute_digest(),
        )
        self._records.append(record)
        self._by_memory_id[memory_id] = record
        self._by_artifact[key] = record
        return record

    def append_round(
        self,
        debate_round: DebateRound,
        *,
        correlation_id: str,
    ) -> tuple[TriadMemoryRecord, ...]:
        debate_round.validate()
        if debate_round.subject_sha != self.subject_sha:
            raise TriadMemoryError("round_subject_mismatch")
        if not correlation_id.strip():
            raise TriadMemoryError("correlation_id_required")

        appended: list[TriadMemoryRecord] = []
        candidates_by_id = {
            item.candidate_id: item for item in debate_round.candidates
        }
        ordered_candidates = sorted(
            debate_round.candidates,
            key=lambda item: (item.revision, item.candidate_id),
        )
        for candidate in ordered_candidates:
            parent_record: TriadMemoryRecord | None = None
            if candidate.parent_candidate_id:
                parent_key = (
                    MemoryArtifactKind.CANDIDATE,
                    candidate.parent_candidate_id,
                )
                parent_record = self._by_artifact.get(parent_key)
                if parent_record is None:
                    parent = candidates_by_id.get(candidate.parent_candidate_id)
                    if parent is None:
                        raise TriadMemoryError("candidate_parent_missing")
                    raise TriadMemoryError("candidate_parent_not_appended")
                if parent_record.task_id != candidate.task_id:
                    raise TriadMemoryError("candidate_parent_task_mismatch")
                if parent_record.revision + 1 != candidate.revision:
                    raise TriadMemoryError(
                        "candidate_revision_not_sequential"
                    )

            parent_memory_id = (
                parent_record.memory_id if parent_record else ""
            )
            candidate_record = self._append(
                task_id=candidate.task_id,
                round_id=debate_round.round_id,
                artifact_kind=MemoryArtifactKind.CANDIDATE,
                artifact_id=candidate.candidate_id,
                artifact_digest=candidate.canonical_digest(),
                payload_json=self._canonical_payload(candidate),
                correlation_id=correlation_id,
                causation_memory_id=parent_memory_id,
                supersedes_memory_id=parent_memory_id,
                parent_artifact_id=candidate.parent_candidate_id,
                revision=candidate.revision,
            )
            appended.append(candidate_record)

        ordered_critiques = sorted(
            debate_round.critiques,
            key=lambda item: item.critique_id,
        )
        for critique in ordered_critiques:
            target_key = (
                MemoryArtifactKind.CANDIDATE,
                critique.candidate_id,
            )
            target = self._by_artifact.get(target_key)
            if target is None:
                raise TriadMemoryError("critique_target_not_appended")
            critique_record = self._append(
                task_id=critique.task_id,
                round_id=debate_round.round_id,
                artifact_kind=MemoryArtifactKind.CRITIQUE,
                artifact_id=critique.critique_id,
                artifact_digest=critique.canonical_digest(),
                payload_json=self._canonical_payload(critique),
                correlation_id=correlation_id,
                causation_memory_id=target.memory_id,
                parent_artifact_id=critique.candidate_id,
            )
            appended.append(critique_record)

        round_record = self._append(
            task_id=debate_round.task_id,
            round_id=debate_round.round_id,
            artifact_kind=MemoryArtifactKind.ROUND,
            artifact_id=debate_round.round_id,
            artifact_digest=debate_round.canonical_digest(),
            payload_json=self._canonical_payload(debate_round),
            correlation_id=correlation_id,
        )
        appended.append(round_record)
        return tuple(appended)

    def get(self, memory_id: str) -> TriadMemoryRecord | None:
        return self._by_memory_id.get(memory_id)

    def find_artifact(
        self,
        kind: MemoryArtifactKind,
        artifact_id: str,
    ) -> TriadMemoryRecord | None:
        return self._by_artifact.get((kind, artifact_id))

    def lineage(self, candidate_id: str) -> tuple[TriadMemoryRecord, ...]:
        current = self.find_artifact(
            MemoryArtifactKind.CANDIDATE,
            candidate_id,
        )
        if current is None:
            raise TriadMemoryError("candidate_memory_missing")
        lineage: list[TriadMemoryRecord] = []
        visited: set[str] = set()
        while current is not None:
            if current.memory_id in visited:
                raise TriadMemoryError("memory_lineage_cycle")
            visited.add(current.memory_id)
            lineage.append(current)
            if not current.supersedes_memory_id:
                break
            current = self.get(current.supersedes_memory_id)
            if current is None:
                raise TriadMemoryError("memory_lineage_broken")
        lineage.reverse()
        return tuple(lineage)

    def task_records(self, task_id: str) -> tuple[TriadMemoryRecord, ...]:
        return tuple(
            record for record in self._records if record.task_id == task_id
        )

    def snapshot(self) -> TriadMemorySnapshot:
        return TriadMemorySnapshot(
            subject_sha=self.subject_sha,
            head_digest=self.head_digest,
            records=self.records,
        )

    @classmethod
    def _validate_replay_links(
        cls,
        record: TriadMemoryRecord,
        seen: dict[str, TriadMemoryRecord],
    ) -> None:
        causation = (
            seen.get(record.causation_memory_id)
            if record.causation_memory_id
            else None
        )
        superseded = (
            seen.get(record.supersedes_memory_id)
            if record.supersedes_memory_id
            else None
        )
        if record.causation_memory_id and causation is None:
            raise TriadMemoryError("causation_not_prior")
        if record.supersedes_memory_id and superseded is None:
            raise TriadMemoryError("supersession_not_prior")

        if record.artifact_kind is MemoryArtifactKind.CANDIDATE:
            if record.revision == 1:
                if causation or superseded or record.parent_artifact_id:
                    raise TriadMemoryError("root_candidate_memory_link_invalid")
            else:
                if causation is None or superseded is None:
                    raise TriadMemoryError("candidate_lineage_link_missing")
                if causation.memory_id != superseded.memory_id:
                    raise TriadMemoryError("candidate_lineage_link_mismatch")
                if causation.artifact_kind is not MemoryArtifactKind.CANDIDATE:
                    raise TriadMemoryError("candidate_parent_kind_invalid")
                if causation.artifact_id != record.parent_artifact_id:
                    raise TriadMemoryError("candidate_parent_memory_mismatch")
                if causation.revision + 1 != record.revision:
                    raise TriadMemoryError("candidate_revision_memory_mismatch")
        elif record.artifact_kind is MemoryArtifactKind.CRITIQUE:
            if causation is None:
                raise TriadMemoryError("critique_causation_missing")
            if causation.artifact_kind is not MemoryArtifactKind.CANDIDATE:
                raise TriadMemoryError("critique_target_kind_invalid")
            if causation.artifact_id != record.parent_artifact_id:
                raise TriadMemoryError("critique_target_memory_mismatch")
            if superseded is not None:
                raise TriadMemoryError("critique_supersession_forbidden")
        else:
            if causation is not None or superseded is not None:
                raise TriadMemoryError("round_memory_link_invalid")

    @classmethod
    def verify_snapshot(
        cls,
        snapshot: TriadMemorySnapshot,
        *,
        expected_subject_sha: str,
        expected_head_digest: str,
    ) -> None:
        if snapshot.subject_sha != expected_subject_sha:
            raise TriadMemoryError("snapshot_subject_mismatch")
        if snapshot.head_digest != expected_head_digest:
            raise TriadMemoryError("snapshot_head_mismatch")

        previous = ""
        seen: dict[str, TriadMemoryRecord] = {}
        seen_artifacts: set[tuple[MemoryArtifactKind, str]] = set()
        for expected_sequence, record in enumerate(
            snapshot.records,
            start=1,
        ):
            if record.sequence != expected_sequence:
                raise TriadMemoryError("snapshot_sequence_invalid")
            if record.subject_sha != expected_subject_sha:
                raise TriadMemoryError("record_subject_mismatch")
            if not isinstance(record.artifact_kind, MemoryArtifactKind):
                raise TriadMemoryError("record_artifact_kind_invalid")
            identities = (
                record.memory_id,
                record.task_id,
                record.round_id,
                record.artifact_id,
                record.artifact_digest,
                record.correlation_id,
            )
            if not all(identities):
                raise TriadMemoryError("record_identity_missing")
            if record.previous_record_digest != previous:
                raise TriadMemoryError("record_chain_broken")
            if record.payload_digest != cls._payload_digest(
                record.payload_json
            ):
                raise TriadMemoryError("record_payload_digest_mismatch")
            calculated_artifact_digest = cls._artifact_digest_from_payload(
                record.artifact_kind,
                record.payload_json,
            )
            if calculated_artifact_digest != record.artifact_digest:
                raise TriadMemoryError("record_artifact_digest_mismatch")
            expected_memory_id = cls._memory_id(
                record.artifact_kind,
                record.artifact_id,
                record.artifact_digest,
            )
            if record.memory_id != expected_memory_id:
                raise TriadMemoryError("record_memory_id_mismatch")
            cls._validate_payload_binding(record)
            cls._validate_replay_links(record, seen)
            if record.record_digest != record.recompute_digest():
                raise TriadMemoryError("record_digest_mismatch")
            if record.memory_id in seen:
                raise TriadMemoryError("duplicate_memory_id")
            artifact_key = (record.artifact_kind, record.artifact_id)
            if artifact_key in seen_artifacts:
                raise TriadMemoryError("duplicate_memory_artifact")
            seen[record.memory_id] = record
            seen_artifacts.add(artifact_key)
            previous = record.record_digest

        calculated_head = (
            snapshot.records[-1].record_digest if snapshot.records else ""
        )
        if calculated_head != snapshot.head_digest:
            raise TriadMemoryError("snapshot_head_not_record_head")
