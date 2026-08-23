from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from enum import StrEnum
from hashlib import sha256

from .triad_debate import CandidateCritique, CandidateProposal, DebateRound


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
    """Append-only, exact-subject memory for public Triad debate artifacts.

    The store records explicit candidate/critique/round artifacts only. It does
    not define or persist hidden chain-of-thought. Every record is bound to the
    exact subject and an append-only digest chain suitable for durable replay.
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
        self._by_artifact: dict[tuple[MemoryArtifactKind, str], TriadMemoryRecord] = {}

    @property
    def head_digest(self) -> str:
        return self._records[-1].record_digest if self._records else ""

    @property
    def records(self) -> tuple[TriadMemoryRecord, ...]:
        return tuple(self._records)

    @staticmethod
    def _canonical_payload(value: object) -> str:
        return json.dumps(asdict(value), sort_keys=True, separators=(",", ":"), default=str)

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
        if len(self._records) >= self.max_records:
            raise TriadMemoryError("memory_capacity_exceeded")
        if not all((task_id.strip(), round_id.strip(), artifact_id.strip(), correlation_id.strip())):
            raise TriadMemoryError("memory_identity_missing")
        if not artifact_digest.strip():
            raise TriadMemoryError("artifact_digest_required")
        if revision < 0:
            raise TriadMemoryError("revision_invalid")

        key = (artifact_kind, artifact_id)
        existing = self._by_artifact.get(key)
        if existing is not None:
            if existing.artifact_digest != artifact_digest:
                raise TriadMemoryError(f"artifact_identity_conflict:{artifact_id}")
            return existing

        for linked_id, error in (
            (causation_memory_id, "causation_memory_missing"),
            (supersedes_memory_id, "superseded_memory_missing"),
        ):
            if linked_id and linked_id not in self._by_memory_id:
                raise TriadMemoryError(f"{error}:{linked_id}")

        memory_id = self._memory_id(artifact_kind, artifact_id, artifact_digest)
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
        record = replace(record, record_digest=record.recompute_digest())
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
        candidates_by_id = {item.candidate_id: item for item in debate_round.candidates}
        ordered_candidates = sorted(
            debate_round.candidates,
            key=lambda item: (item.revision, item.candidate_id),
        )
        for candidate in ordered_candidates:
            parent_record: TriadMemoryRecord | None = None
            if candidate.parent_candidate_id:
                parent_record = self._by_artifact.get(
                    (MemoryArtifactKind.CANDIDATE, candidate.parent_candidate_id)
                )
                if parent_record is None:
                    parent = candidates_by_id.get(candidate.parent_candidate_id)
                    if parent is None:
                        raise TriadMemoryError("candidate_parent_missing")
                    raise TriadMemoryError("candidate_parent_not_appended")
                if parent_record.task_id != candidate.task_id:
                    raise TriadMemoryError("candidate_parent_task_mismatch")
                if parent_record.revision + 1 != candidate.revision:
                    raise TriadMemoryError("candidate_revision_not_sequential")

            candidate_record = self._append(
                task_id=candidate.task_id,
                round_id=debate_round.round_id,
                artifact_kind=MemoryArtifactKind.CANDIDATE,
                artifact_id=candidate.candidate_id,
                artifact_digest=candidate.canonical_digest(),
                payload_json=self._canonical_payload(candidate),
                correlation_id=correlation_id,
                causation_memory_id=parent_record.memory_id if parent_record else "",
                supersedes_memory_id=parent_record.memory_id if parent_record else "",
                parent_artifact_id=candidate.parent_candidate_id,
                revision=candidate.revision,
            )
            appended.append(candidate_record)

        for critique in sorted(debate_round.critiques, key=lambda item: item.critique_id):
            target = self._by_artifact.get((MemoryArtifactKind.CANDIDATE, critique.candidate_id))
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
        current = self.find_artifact(MemoryArtifactKind.CANDIDATE, candidate_id)
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
        return tuple(record for record in self._records if record.task_id == task_id)

    def snapshot(self) -> TriadMemorySnapshot:
        return TriadMemorySnapshot(
            subject_sha=self.subject_sha,
            head_digest=self.head_digest,
            records=self.records,
        )

    @staticmethod
    def verify_snapshot(
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
        seen_memory_ids: set[str] = set()
        seen_artifacts: set[tuple[MemoryArtifactKind, str]] = set()
        for expected_sequence, record in enumerate(snapshot.records, start=1):
            if record.sequence != expected_sequence:
                raise TriadMemoryError("snapshot_sequence_invalid")
            if record.subject_sha != expected_subject_sha:
                raise TriadMemoryError("record_subject_mismatch")
            if record.previous_record_digest != previous:
                raise TriadMemoryError("record_chain_broken")
            if record.payload_digest != TriadMemoryStore._payload_digest(record.payload_json):
                raise TriadMemoryError("record_payload_digest_mismatch")
            if record.record_digest != record.recompute_digest():
                raise TriadMemoryError("record_digest_mismatch")
            if record.memory_id in seen_memory_ids:
                raise TriadMemoryError("duplicate_memory_id")
            key = (record.artifact_kind, record.artifact_id)
            if key in seen_artifacts:
                raise TriadMemoryError("duplicate_memory_artifact")
            seen_memory_ids.add(record.memory_id)
            seen_artifacts.add(key)
            if record.causation_memory_id and record.causation_memory_id not in seen_memory_ids:
                raise TriadMemoryError("causation_not_prior")
            if record.supersedes_memory_id and record.supersedes_memory_id not in seen_memory_ids:
                raise TriadMemoryError("supersession_not_prior")
            previous = record.record_digest

        calculated_head = snapshot.records[-1].record_digest if snapshot.records else ""
        if calculated_head != snapshot.head_digest:
            raise TriadMemoryError("snapshot_head_not_record_head")
