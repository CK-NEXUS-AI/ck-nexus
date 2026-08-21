from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic
from collections.abc import Iterable
from uuid import uuid4

from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.provider_router import ProviderRouteError, ProviderRouter


class ExperimentDecision(StrEnum):
    RETEST = "retest"
    REJECT = "reject"
    PROMOTION_CANDIDATE = "promotion_candidate"


@dataclass(frozen=True, slots=True)
class AssistantRun:
    provider: str
    success: bool
    latency_ms: int
    output: str | None
    output_digest: str | None
    error_code: str | None = None

    def evidence_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "success": self.success,
            "latency_ms": self.latency_ms,
            "output_digest": self.output_digest,
            "error_code": self.error_code,
        }


@dataclass(frozen=True, slots=True)
class VariantScore:
    variant_id: str
    quality: float
    reliability: float
    latency_ms: int
    cost_score: float
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (self.quality, self.reliability, self.cost_score):
            if not 0.0 <= value <= 1.0:
                raise ValueError("normalized experiment scores must be between 0 and 1")
        if self.latency_ms < 0:
            raise ValueError("latency_ms cannot be negative")


@dataclass(frozen=True, slots=True)
class ExperimentOutcome:
    experiment_id: str
    baseline_id: str
    winner_id: str | None
    improvement: float
    decision: ExperimentDecision
    verified_by: str
    scores: tuple[tuple[str, float], ...]


class MultiAssistantEvaluationHarness:
    """Runs explicitly selected registered providers concurrently.

    Provider adapters and credentials stay behind ProviderRouter. Raw outputs are
    returned to the caller for evaluation, but only digests belong in evidence.
    """

    def __init__(self, router: ProviderRouter) -> None:
        self.router = router

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def run(
        self,
        prompt: str,
        *,
        provider_names: Iterable[str],
        required_capabilities: Iterable[str] = (),
    ) -> tuple[AssistantRun, ...]:
        names = tuple(
            dict.fromkeys(name.strip() for name in provider_names if name.strip())
        )
        if not names:
            raise ValueError("at least one provider must be selected")

        async def invoke(name: str) -> AssistantRun:
            started = monotonic()
            try:
                selection = await self.router.invoke_named(
                    name,
                    prompt,
                    required_capabilities=required_capabilities,
                )
            except ProviderRouteError as exc:
                return AssistantRun(
                    provider=name,
                    success=False,
                    latency_ms=max(0, int((monotonic() - started) * 1000)),
                    output=None,
                    output_digest=None,
                    error_code=exc.code,
                )
            output = selection.output
            return AssistantRun(
                provider=name,
                success=True,
                latency_ms=max(0, int((monotonic() - started) * 1000)),
                output=output,
                output_digest=self._digest(output),
            )

        return tuple(await asyncio.gather(*(invoke(name) for name in names)))


class IdeaAutoExperimenter:
    """Evidence-first baseline-vs-candidate experiment controller.

    It may calculate and propose a winner, but never self-approves promotion.
    """

    SELF_VERIFIERS = frozenset({"agnes", "self", "model", "assistant"})

    def __init__(
        self,
        ledger: AppendOnlyLedger,
        *,
        minimum_improvement: float = 0.05,
    ) -> None:
        if minimum_improvement < 0:
            raise ValueError("minimum_improvement cannot be negative")
        self.ledger = ledger
        self.minimum_improvement = minimum_improvement

    @staticmethod
    def _score(item: VariantScore) -> float:
        latency = 1.0 / (1.0 + (item.latency_ms / 1000.0))
        return (
            (item.quality * 0.45)
            + (item.reliability * 0.30)
            + (item.cost_score * 0.15)
            + (latency * 0.10)
        )

    def record_parallel_runs(
        self,
        *,
        experiment_id: str,
        prompt_digest: str,
        runs: Iterable[AssistantRun],
    ) -> str:
        rows = tuple(runs)
        event = self.ledger.append(
            "idea_experiment_parallel_runs",
            {
                "experiment_id": experiment_id,
                "prompt_digest": prompt_digest,
                "runs": [row.evidence_dict() for row in rows],
                "raw_outputs_stored": False,
            },
        )
        return str(event["hash"])

    def evaluate(
        self,
        *,
        baseline_id: str,
        variants: Iterable[VariantScore],
        hypothesis: str,
        verified_by: str,
        experiment_id: str | None = None,
    ) -> ExperimentOutcome:
        verifier = verified_by.strip().lower()
        if not verifier or verifier in self.SELF_VERIFIERS:
            raise PermissionError("independent or human verification is required")

        rows = tuple(variants)
        if len(rows) < 2:
            raise ValueError("baseline comparison requires at least two variants")
        ids = [row.variant_id for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError("variant ids must be unique")
        if baseline_id not in ids:
            raise ValueError("baseline variant is missing")
        if any(not row.evidence_refs for row in rows):
            raise ValueError("every variant requires evidence")

        scores = {row.variant_id: self._score(row) for row in rows}
        winner_id = max(scores, key=scores.__getitem__)
        improvement = scores[winner_id] - scores[baseline_id]
        if winner_id == baseline_id:
            decision = ExperimentDecision.REJECT
            winner: str | None = None
        elif improvement >= self.minimum_improvement:
            decision = ExperimentDecision.PROMOTION_CANDIDATE
            winner = winner_id
        else:
            decision = ExperimentDecision.RETEST
            winner = winner_id

        exp_id = experiment_id or f"agnes_exp_{uuid4().hex}"
        event = self.ledger.append(
            "idea_experiment_evaluated",
            {
                "experiment_id": exp_id,
                "hypothesis_digest": hashlib.sha256(
                    hypothesis.encode("utf-8")
                ).hexdigest(),
                "baseline_id": baseline_id,
                "winner_id": winner,
                "improvement": round(improvement, 8),
                "decision": decision.value,
                "verified_by": verified_by,
                "scores": {key: round(value, 8) for key, value in scores.items()},
                "evidence_refs": {
                    row.variant_id: list(row.evidence_refs) for row in rows
                },
                "auto_promote": False,
                "production_mutation": False,
            },
        )
        if not event.get("hash"):
            raise RuntimeError("experiment evidence was not sealed")
        return ExperimentOutcome(
            experiment_id=exp_id,
            baseline_id=baseline_id,
            winner_id=winner,
            improvement=improvement,
            decision=decision,
            verified_by=verified_by,
            scores=tuple(sorted(scores.items())),
        )
