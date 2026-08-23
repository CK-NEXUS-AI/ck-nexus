from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256

from .triad_scheduler import TriadRole


class DebateContractError(ValueError):
    """Raised when a debate artifact violates Triad separation or subject binding."""


class CandidateStatus(StrEnum):
    PROPOSED = "PROPOSED"
    REVISED = "REVISED"
    MEASURED_NOT_VERIFIED = "MEASURED_NOT_VERIFIED"
    REJECTED = "REJECTED"


class CritiqueSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    BLOCKING = "BLOCKING"


_VERIFICATION_CEILING = "MEASURED_NOT_VERIFIED"


def _require_text(value: str, field: str) -> str:
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise DebateContractError(f"{field}_required")
    return text


def _require_unique_text(values: tuple[str, ...], field: str) -> tuple[str, ...]:
    cleaned = tuple(_require_text(value, field) for value in values)
    if len(cleaned) != len(set(cleaned)):
        raise DebateContractError(f"duplicate_{field}")
    return cleaned


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    candidate_id: str
    task_id: str
    subject_sha: str
    proposer_role: TriadRole
    statement: str
    rationale: str
    expected_delta: str
    assumptions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    parent_candidate_id: str = ""
    revision: int = 1
    status: CandidateStatus = CandidateStatus.PROPOSED

    def validate(self, expected_subject_sha: str) -> None:
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.task_id, "task_id")
        _require_text(self.statement, "statement")
        _require_text(self.rationale, "rationale")
        _require_text(self.expected_delta, "expected_delta")
        if self.subject_sha != expected_subject_sha:
            raise DebateContractError("subject_mismatch")
        if not isinstance(self.status, CandidateStatus):
            raise DebateContractError("candidate_status_invalid")
        if self.proposer_role is not TriadRole.BUILDER:
            raise DebateContractError("candidate_proposer_must_be_builder")
        if self.revision < 1:
            raise DebateContractError("candidate_revision_invalid")
        if (
            self.revision > 1 or self.status is CandidateStatus.REVISED
        ) and not self.parent_candidate_id:
            raise DebateContractError("revised_candidate_parent_required")
        _require_unique_text(self.assumptions, "assumption")
        evidence_refs = _require_unique_text(self.evidence_refs, "evidence_ref")
        if self.status is CandidateStatus.MEASURED_NOT_VERIFIED and not evidence_refs:
            raise DebateContractError("measured_candidate_evidence_required")

    def canonical_digest(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()

    def semantic_digest(self) -> str:
        payload = {
            "task_id": self.task_id,
            "statement": self.statement.strip(),
            "expected_delta": self.expected_delta.strip(),
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateCritique:
    critique_id: str
    candidate_id: str
    task_id: str
    subject_sha: str
    critic_role: TriadRole
    severity: CritiqueSeverity
    findings: tuple[str, ...]
    counter_evidence_refs: tuple[str, ...] = ()
    requested_changes: tuple[str, ...] = ()

    def validate(self, expected_subject_sha: str) -> None:
        _require_text(self.critique_id, "critique_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.task_id, "task_id")
        if self.subject_sha != expected_subject_sha:
            raise DebateContractError("subject_mismatch")
        if not isinstance(self.severity, CritiqueSeverity):
            raise DebateContractError("critique_severity_invalid")
        if self.critic_role is not TriadRole.CRITIC:
            raise DebateContractError("critique_author_must_be_critic")
        if not _require_unique_text(self.findings, "finding"):
            raise DebateContractError("critique_findings_required")
        _require_unique_text(self.counter_evidence_refs, "counter_evidence_ref")
        _require_unique_text(self.requested_changes, "requested_change")

    def canonical_digest(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DebateRound:
    round_id: str
    task_id: str
    subject_sha: str
    candidates: tuple[CandidateProposal, ...]
    critiques: tuple[CandidateCritique, ...] = ()

    @property
    def verification_ceiling(self) -> str:
        return _VERIFICATION_CEILING

    def validate(self) -> None:
        _require_text(self.round_id, "round_id")
        _require_text(self.task_id, "task_id")
        _require_text(self.subject_sha, "subject_sha")
        if not self.candidates:
            raise DebateContractError("debate_candidates_required")
        if len(self.candidates) > 9:
            raise DebateContractError("debate_candidate_limit_exceeded")

        candidate_ids: set[str] = set()
        semantic_digests: set[str] = set()
        for candidate in self.candidates:
            candidate.validate(self.subject_sha)
            if candidate.task_id != self.task_id:
                raise DebateContractError("candidate_task_mismatch")
            if candidate.candidate_id in candidate_ids:
                raise DebateContractError("duplicate_candidate_id")
            semantic_digest = candidate.semantic_digest()
            if semantic_digest in semantic_digests:
                raise DebateContractError("duplicate_candidate_semantics")
            candidate_ids.add(candidate.candidate_id)
            semantic_digests.add(semantic_digest)

        critique_ids: set[str] = set()
        for critique in self.critiques:
            critique.validate(self.subject_sha)
            if critique.task_id != self.task_id:
                raise DebateContractError("critique_task_mismatch")
            if critique.critique_id in critique_ids:
                raise DebateContractError("duplicate_critique_id")
            if critique.candidate_id not in candidate_ids:
                raise DebateContractError("critique_candidate_missing")
            critique_ids.add(critique.critique_id)

    def canonical_digest(self) -> str:
        self.validate()
        payload = {
            "round_id": self.round_id,
            "task_id": self.task_id,
            "subject_sha": self.subject_sha,
            "verification_ceiling": self.verification_ceiling,
            "candidates": [
                asdict(item) for item in sorted(self.candidates, key=lambda item: item.candidate_id)
            ],
            "critiques": [
                asdict(item) for item in sorted(self.critiques, key=lambda item: item.critique_id)
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()
