from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256

from .triad_scheduler import TriadRole


class DebateSchemaError(ValueError):
    """Raised when debate/candidate provenance is invalid."""


@dataclass(frozen=True, slots=True)
class CandidateProposal:
    proposal_id: str
    candidate_id: str
    round_id: str
    subject_sha: str
    work_id: str
    capability: str
    revision: int
    author_role: TriadRole
    thesis: str
    claims: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    parent_proposal_id: str | None = None
    verification_ceiling: str = "MEASURED_NOT_VERIFIED"

    def validate(self) -> None:
        required = {
            "proposal_id": self.proposal_id,
            "candidate_id": self.candidate_id,
            "round_id": self.round_id,
            "subject_sha": self.subject_sha,
            "work_id": self.work_id,
            "capability": self.capability,
            "thesis": self.thesis,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise DebateSchemaError(f"missing_fields:{','.join(sorted(missing))}")
        if self.revision < 1:
            raise DebateSchemaError("revision_must_be_positive")
        if self.author_role not in {TriadRole.BUILDER, TriadRole.CRITIC}:
            raise DebateSchemaError("candidate_author_role_not_allowed")
        if not self.claims or any(not claim for claim in self.claims):
            raise DebateSchemaError("claims_required")
        if self.revision == 1 and self.parent_proposal_id is not None:
            raise DebateSchemaError("root_candidate_cannot_have_parent")
        if self.revision > 1 and not self.parent_proposal_id:
            raise DebateSchemaError("revised_candidate_requires_parent")
        if self.parent_proposal_id == self.proposal_id:
            raise DebateSchemaError("candidate_cannot_parent_itself")
        if self.verification_ceiling != "MEASURED_NOT_VERIFIED":
            raise DebateSchemaError("candidate_cannot_self_promote")

    def digest(self) -> str:
        self.validate()
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateCritique:
    critique_id: str
    round_id: str
    subject_sha: str
    target_proposal_id: str
    objections: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    author_role: TriadRole = TriadRole.CRITIC

    def validate(self) -> None:
        if not all((self.critique_id, self.round_id, self.subject_sha, self.target_proposal_id)):
            raise DebateSchemaError("critique_identity_missing")
        if self.author_role is not TriadRole.CRITIC:
            raise DebateSchemaError("critique_author_must_be_critic")
        if not self.objections or any(not item for item in self.objections):
            raise DebateSchemaError("critique_objections_required")

    def digest(self) -> str:
        self.validate()
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class DebateRound:
    round_id: str
    subject_sha: str
    work_id: str
    capability: str
    proposals: tuple[CandidateProposal, ...]
    critiques: tuple[CandidateCritique, ...] = ()

    def validate(self) -> None:
        if not all((self.round_id, self.subject_sha, self.work_id, self.capability)):
            raise DebateSchemaError("round_identity_missing")
        if not self.proposals:
            raise DebateSchemaError("round_requires_candidate")

        by_id: dict[str, CandidateProposal] = {}
        for proposal in self.proposals:
            proposal.validate()
            if proposal.proposal_id in by_id:
                raise DebateSchemaError(f"duplicate_proposal_id:{proposal.proposal_id}")
            if proposal.round_id != self.round_id:
                raise DebateSchemaError("proposal_round_mismatch")
            if proposal.subject_sha != self.subject_sha:
                raise DebateSchemaError("proposal_subject_mismatch")
            if proposal.work_id != self.work_id or proposal.capability != self.capability:
                raise DebateSchemaError("proposal_work_identity_mismatch")
            by_id[proposal.proposal_id] = proposal

        seen_revision: set[tuple[str, int]] = set()
        for proposal in self.proposals:
            revision_key = (proposal.candidate_id, proposal.revision)
            if revision_key in seen_revision:
                raise DebateSchemaError("duplicate_candidate_revision")
            seen_revision.add(revision_key)
            if proposal.parent_proposal_id is None:
                continue
            parent = by_id.get(proposal.parent_proposal_id)
            if parent is None:
                raise DebateSchemaError(f"orphan_parent:{proposal.parent_proposal_id}")
            if parent.candidate_id != proposal.candidate_id:
                raise DebateSchemaError("parent_candidate_lineage_mismatch")
            if parent.revision + 1 != proposal.revision:
                raise DebateSchemaError("parent_revision_not_immediate_predecessor")

        critique_ids: set[str] = set()
        for critique in self.critiques:
            critique.validate()
            if critique.critique_id in critique_ids:
                raise DebateSchemaError(f"duplicate_critique_id:{critique.critique_id}")
            critique_ids.add(critique.critique_id)
            if critique.round_id != self.round_id:
                raise DebateSchemaError("critique_round_mismatch")
            if critique.subject_sha != self.subject_sha:
                raise DebateSchemaError("critique_subject_mismatch")
            if critique.target_proposal_id not in by_id:
                raise DebateSchemaError("critique_target_missing")

    def candidate_heads(self) -> tuple[CandidateProposal, ...]:
        self.validate()
        heads: dict[str, CandidateProposal] = {}
        for proposal in self.proposals:
            current = heads.get(proposal.candidate_id)
            if current is None or proposal.revision > current.revision:
                heads[proposal.candidate_id] = proposal
        return tuple(sorted(heads.values(), key=lambda item: item.candidate_id))

    def digest(self) -> str:
        self.validate()
        payload = {
            "round_id": self.round_id,
            "subject_sha": self.subject_sha,
            "work_id": self.work_id,
            "capability": self.capability,
            "proposals": [asdict(item) for item in self.proposals],
            "critiques": [asdict(item) for item in self.critiques],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(raw.encode("utf-8")).hexdigest()
