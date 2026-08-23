from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Any


class TriadPipelineError(ValueError):
    """Raised when a Triad pipeline checkpoint cannot be trusted."""


class TriadPipelineStage(StrEnum):
    EVENT_BUS = "EVENT_BUS"
    PARALLEL_SCHEDULER = "PARALLEL_SCHEDULER"
    DEBATE_CANDIDATE = "DEBATE_CANDIDATE"
    TRIAD_MEMORY = "TRIAD_MEMORY"
    EVIDENCE_EVALUATOR = "EVIDENCE_EVALUATOR"
    PULSE_15_20 = "PULSE_15_20"
    LEARNING_CONSOLIDATOR = "LEARNING_CONSOLIDATOR"
    DASHBOARD = "DASHBOARD"


CANONICAL_STAGE_ORDER = (
    TriadPipelineStage.EVENT_BUS,
    TriadPipelineStage.PARALLEL_SCHEDULER,
    TriadPipelineStage.DEBATE_CANDIDATE,
    TriadPipelineStage.TRIAD_MEMORY,
    TriadPipelineStage.EVIDENCE_EVALUATOR,
    TriadPipelineStage.PULSE_15_20,
    TriadPipelineStage.LEARNING_CONSOLIDATOR,
    TriadPipelineStage.DASHBOARD,
)
_STAGE_INDEX = {stage: index for index, stage in enumerate(CANONICAL_STAGE_ORDER)}
_TRUTH_STATE = "MEASURED_NOT_VERIFIED"


def _require_text(value: str, field: str) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise TriadPipelineError(f"{field}_required")
    return text


def _require_hex(value: str, field: str, lengths: tuple[int, ...]) -> str:
    text = _require_text(value, field).lower()
    if len(text) not in lengths:
        raise TriadPipelineError(f"{field}_invalid")
    try:
        int(text, 16)
    except ValueError as exc:
        raise TriadPipelineError(f"{field}_invalid") from exc
    return text


@dataclass(frozen=True, slots=True)
class TriadStageBinding:
    stage: TriadPipelineStage
    subject_sha: str
    source_commit: str
    artifact_digest: str
    truth_state: str = _TRUTH_STATE
    independent_verification_required: bool = True
    mutation_allowed: bool = False
    production_promotion_allowed: bool = False

    def validate(self, expected_subject_sha: str) -> None:
        if not isinstance(self.stage, TriadPipelineStage):
            raise TriadPipelineError("stage_invalid")
        if self.subject_sha != expected_subject_sha:
            raise TriadPipelineError("stage_subject_mismatch")
        _require_hex(self.source_commit, "stage_source_commit", (40, 64))
        _require_hex(self.artifact_digest, "stage_artifact_digest", (64,))
        if self.truth_state != _TRUTH_STATE:
            raise TriadPipelineError("stage_truth_state_invalid")
        if self.independent_verification_required is not True:
            raise TriadPipelineError("independent_verification_required")
        if self.mutation_allowed is not False:
            raise TriadPipelineError("stage_mutation_forbidden")
        if self.production_promotion_allowed is not False:
            raise TriadPipelineError("stage_production_promotion_forbidden")

    def canonical_digest(self) -> str:
        raw = json.dumps(
            asdict(self),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TriadPipelineManifest:
    pipeline_id: str
    subject_sha: str
    implementation_sha: str
    stages: tuple[TriadStageBinding, ...]
    parent_manifest_digest: str = ""
    supersedes_manifest_digest: str = ""
    fork_reason: str = ""
    schema_version: str = "1.0"

    @property
    def truth_state(self) -> str:
        return _TRUTH_STATE

    def _ordered_stages(self) -> tuple[TriadStageBinding, ...]:
        return tuple(sorted(self.stages, key=lambda item: _STAGE_INDEX[item.stage]))

    def validate(self, expected_subject_sha: str | None = None) -> None:
        _require_text(self.pipeline_id, "pipeline_id")
        _require_text(self.subject_sha, "subject_sha")
        _require_hex(self.implementation_sha, "implementation_sha", (40, 64))
        if self.schema_version != "1.0":
            raise TriadPipelineError("pipeline_schema_invalid")
        if expected_subject_sha is not None and self.subject_sha != expected_subject_sha:
            raise TriadPipelineError("pipeline_subject_mismatch")

        if len(self.stages) != len(CANONICAL_STAGE_ORDER):
            raise TriadPipelineError("pipeline_stage_count_invalid")
        seen: set[TriadPipelineStage] = set()
        for binding in self.stages:
            binding.validate(self.subject_sha)
            if binding.stage in seen:
                raise TriadPipelineError("duplicate_pipeline_stage")
            seen.add(binding.stage)
        if seen != set(CANONICAL_STAGE_ORDER):
            raise TriadPipelineError("pipeline_stage_set_incomplete")

        if self.parent_manifest_digest:
            _require_hex(self.parent_manifest_digest, "parent_manifest_digest", (64,))
        if self.supersedes_manifest_digest:
            _require_hex(
                self.supersedes_manifest_digest,
                "supersedes_manifest_digest",
                (64,),
            )
        if self.fork_reason and not self.parent_manifest_digest:
            raise TriadPipelineError("fork_parent_required")

    def canonical_payload(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema_version": self.schema_version,
            "pipeline_id": self.pipeline_id,
            "subject_sha": self.subject_sha,
            "implementation_sha": self.implementation_sha,
            "truth_state": self.truth_state,
            "independent_verification_required": True,
            "verified_claim_allowed": False,
            "adoption_allowed": False,
            "mutation_allowed": False,
            "production_promotion_allowed": False,
            "parent_manifest_digest": self.parent_manifest_digest,
            "supersedes_manifest_digest": self.supersedes_manifest_digest,
            "fork_reason": self.fork_reason,
            "stages": [asdict(item) for item in self._ordered_stages()],
        }

    def canonical_digest(self) -> str:
        raw = json.dumps(
            self.canonical_payload(),
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TriadPipelineRecord:
    sequence: int
    manifest: TriadPipelineManifest
    manifest_digest: str
    previous_record_digest: str
    record_digest: str

    def recompute_digest(self) -> str:
        payload = {
            "sequence": self.sequence,
            "manifest_digest": self.manifest_digest,
            "previous_record_digest": self.previous_record_digest,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class TriadPipelineSnapshot:
    subject_sha: str
    head_record_digest: str
    records: tuple[TriadPipelineRecord, ...]


class TriadPipelineLedger:
    """Append-only provenance ledger for complete AGNES Triad pipeline checkpoints.

    The ledger binds every stage by digest, preserves explicit parent/supersession
    links, permits controlled forks only from known prior manifests, and never
    grants VERIFIED, adoption, mutation, or production-promotion authority.
    """

    def __init__(self, subject_sha: str) -> None:
        self.subject_sha = _require_text(subject_sha, "subject_sha")
        self._records: list[TriadPipelineRecord] = []
        self._by_pipeline_id: dict[str, TriadPipelineRecord] = {}
        self._manifest_digests: set[str] = set()

    @property
    def head_record_digest(self) -> str:
        return self._records[-1].record_digest if self._records else ""

    @property
    def head_manifest_digest(self) -> str:
        return self._records[-1].manifest_digest if self._records else ""

    def append(self, manifest: TriadPipelineManifest) -> TriadPipelineRecord:
        manifest.validate(self.subject_sha)
        manifest_digest = manifest.canonical_digest()
        existing = self._by_pipeline_id.get(manifest.pipeline_id)
        if existing is not None:
            if existing.manifest_digest != manifest_digest:
                raise TriadPipelineError("pipeline_identity_conflict")
            return existing

        if not self._records:
            if manifest.parent_manifest_digest:
                raise TriadPipelineError("root_pipeline_parent_forbidden")
            if manifest.supersedes_manifest_digest:
                raise TriadPipelineError("root_pipeline_supersession_forbidden")
        else:
            parent = manifest.parent_manifest_digest
            if not parent:
                raise TriadPipelineError("pipeline_parent_required")
            if parent not in self._manifest_digests:
                raise TriadPipelineError("pipeline_parent_unknown")
            if parent != self.head_manifest_digest and not manifest.fork_reason.strip():
                raise TriadPipelineError("pipeline_fork_reason_required")
            if (
                manifest.supersedes_manifest_digest
                and manifest.supersedes_manifest_digest not in self._manifest_digests
            ):
                raise TriadPipelineError("pipeline_supersedes_unknown")

        sequence = len(self._records) + 1
        previous = self.head_record_digest
        provisional = TriadPipelineRecord(
            sequence=sequence,
            manifest=manifest,
            manifest_digest=manifest_digest,
            previous_record_digest=previous,
            record_digest="",
        )
        record = TriadPipelineRecord(
            sequence=sequence,
            manifest=manifest,
            manifest_digest=manifest_digest,
            previous_record_digest=previous,
            record_digest=provisional.recompute_digest(),
        )
        self._records.append(record)
        self._by_pipeline_id[manifest.pipeline_id] = record
        self._manifest_digests.add(manifest_digest)
        return record

    def snapshot(self) -> TriadPipelineSnapshot:
        return TriadPipelineSnapshot(
            subject_sha=self.subject_sha,
            head_record_digest=self.head_record_digest,
            records=tuple(self._records),
        )

    @classmethod
    def verify_snapshot(
        cls,
        snapshot: TriadPipelineSnapshot,
        *,
        expected_subject_sha: str,
        expected_head_record_digest: str,
    ) -> None:
        if snapshot.subject_sha != expected_subject_sha:
            raise TriadPipelineError("snapshot_subject_mismatch")
        if snapshot.head_record_digest != expected_head_record_digest:
            raise TriadPipelineError("snapshot_head_mismatch")

        manifest_digests: set[str] = set()
        pipeline_ids: set[str] = set()
        previous_record_digest = ""
        previous_manifest_digest = ""
        for expected_sequence, record in enumerate(snapshot.records, start=1):
            record.manifest.validate(expected_subject_sha)
            calculated_manifest = record.manifest.canonical_digest()
            if record.sequence != expected_sequence:
                raise TriadPipelineError("pipeline_sequence_invalid")
            if record.manifest.pipeline_id in pipeline_ids:
                raise TriadPipelineError("duplicate_pipeline_id")
            if record.manifest_digest != calculated_manifest:
                raise TriadPipelineError("pipeline_manifest_digest_mismatch")
            if record.previous_record_digest != previous_record_digest:
                raise TriadPipelineError("pipeline_record_chain_invalid")
            if record.record_digest != record.recompute_digest():
                raise TriadPipelineError("pipeline_record_digest_mismatch")

            parent = record.manifest.parent_manifest_digest
            supersedes = record.manifest.supersedes_manifest_digest
            if expected_sequence == 1:
                if parent or supersedes:
                    raise TriadPipelineError("root_pipeline_link_invalid")
            else:
                if not parent or parent not in manifest_digests:
                    raise TriadPipelineError("pipeline_parent_unknown")
                if parent != previous_manifest_digest and not record.manifest.fork_reason.strip():
                    raise TriadPipelineError("pipeline_fork_reason_required")
                if supersedes and supersedes not in manifest_digests:
                    raise TriadPipelineError("pipeline_supersedes_unknown")

            manifest_digests.add(record.manifest_digest)
            pipeline_ids.add(record.manifest.pipeline_id)
            previous_record_digest = record.record_digest
            previous_manifest_digest = record.manifest_digest

        calculated_head = snapshot.records[-1].record_digest if snapshot.records else ""
        if calculated_head != snapshot.head_record_digest:
            raise TriadPipelineError("snapshot_head_invalid")
