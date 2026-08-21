from __future__ import annotations

from pydantic import BaseModel, Field


class ReproducibleResearchArtifact(BaseModel):
    artifact_id: str
    source_commit: str
    source_tree: str
    environment_digest: str
    input_digests: tuple[str, ...] = ()
    output_digests: tuple[str, ...] = ()
    evaluator_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    random_seed: int | None = None
    provider_versions: dict[str, str] = Field(default_factory=dict)
    production_evidence: bool = False

    def validate_reproducibility(self) -> bool:
        if not self.source_commit or not self.source_tree or not self.environment_digest:
            return False
        if not self.input_digests or not self.output_digests or not self.evidence_ids:
            return False
        if len(set(self.evaluator_ids)) != len(self.evaluator_ids):
            return False
        for version in self.provider_versions.values():
            if not version.strip() or version.strip().lower() in {"latest", "main", "head"}:
                return False
        return True


class EvaluatorFleetReceipt(BaseModel):
    subject_id: str
    evaluator_ids: tuple[str, ...]
    independent_evaluator_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    safety_veto: bool = False
    minimum_quorum: int = Field(default=2, ge=2, le=50)

    def quorum_met(self) -> bool:
        independent = set(self.independent_evaluator_ids)
        all_evaluators = set(self.evaluator_ids)
        if not independent.issubset(all_evaluators):
            return False
        if self.safety_veto or not self.evidence_ids:
            return False
        return len(independent) >= self.minimum_quorum
