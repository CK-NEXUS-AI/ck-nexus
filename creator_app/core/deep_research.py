from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ResearchDecision(StrEnum):
    CONTINUE = "continue"
    READY_FOR_VERIFICATION = "ready_for_verification"
    BLOCKED = "blocked"


class ResearchGap(BaseModel):
    gap_id: str
    gap_digest: str
    severity: int = Field(default=1, ge=1, le=5)
    evidence_ids: tuple[str, ...] = ()


class ResearchIteration(BaseModel):
    iteration_id: str
    objective_digest: str
    source_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    unresolved_gap_ids: tuple[str, ...] = ()
    external_write_requested: bool = False


class DeepResearchState(BaseModel):
    research_id: str
    question_digest: str
    iterations: tuple[ResearchIteration, ...] = ()
    gaps: tuple[ResearchGap, ...] = ()
    finalized: bool = False


class DeepResearchPolicy(BaseModel):
    max_iterations: int = Field(default=6, ge=1, le=20)
    max_sources_total: int = Field(default=200, ge=1, le=5000)
    minimum_distinct_sources: int = Field(default=3, ge=1, le=100)

    def evaluate(self, state: DeepResearchState) -> ResearchDecision:
        """Evaluate whether iterative research should continue, verify, or fail closed."""
        if state.finalized:
            return ResearchDecision.BLOCKED
        if len(state.iterations) > self.max_iterations:
            return ResearchDecision.BLOCKED
        if any(item.external_write_requested for item in state.iterations):
            return ResearchDecision.BLOCKED
        if any(not item.evidence_ids for item in state.iterations):
            return ResearchDecision.BLOCKED

        source_ids = {
            source_id
            for item in state.iterations
            for source_id in item.source_ids
        }
        if len(source_ids) > self.max_sources_total:
            return ResearchDecision.BLOCKED

        unresolved = {
            gap_id
            for item in state.iterations
            for gap_id in item.unresolved_gap_ids
        }
        high_severity = {
            gap.gap_id
            for gap in state.gaps
            if gap.severity >= 4 and gap.gap_id in unresolved
        }

        at_limit = len(state.iterations) >= self.max_iterations
        if high_severity and at_limit:
            return ResearchDecision.BLOCKED
        if unresolved:
            return ResearchDecision.CONTINUE
        if len(source_ids) < self.minimum_distinct_sources:
            return ResearchDecision.BLOCKED if at_limit else ResearchDecision.CONTINUE
        return ResearchDecision.READY_FOR_VERIFICATION

    def next_iteration_number(self, state: DeepResearchState) -> int:
        if self.evaluate(state) == ResearchDecision.BLOCKED:
            raise ValueError("research_state_blocked")
        if len(state.iterations) >= self.max_iterations:
            raise ValueError("research_iteration_budget_exhausted")
        return len(state.iterations) + 1
