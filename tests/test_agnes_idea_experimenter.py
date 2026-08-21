from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from creator_app.agnes_idea_experimenter import (
    ExperimentDecision,
    IdeaAutoExperimenter,
    MultiAssistantEvaluationHarness,
    VariantScore,
)
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.provider_router import (
    ProviderCapabilities,
    ProviderKind,
    ProviderRouter,
)


class FakeProvider:
    kind = ProviderKind.MOCK
    capabilities = ProviderCapabilities(features=frozenset({"text"}), models=("fake",))

    def __init__(
        self, name: str, output: str | None = None, *, fail: bool = False
    ) -> None:
        self.name = name
        self.output = output or f"output:{name}"
        self.fail = fail

    def is_available(self) -> bool:
        return True

    async def invoke(self, prompt: str) -> str:
        if self.fail:
            raise RuntimeError("provider failed")
        await asyncio.sleep(0)
        return f"{self.output}:{prompt}"


def ledger(tmp_path: Path) -> AppendOnlyLedger:
    return AppendOnlyLedger(tmp_path / "experiment.jsonl")


def score(
    variant_id: str,
    *,
    quality: float,
    reliability: float,
    cost_score: float,
    latency_ms: int = 100,
) -> VariantScore:
    return VariantScore(
        variant_id=variant_id,
        quality=quality,
        reliability=reliability,
        latency_ms=latency_ms,
        cost_score=cost_score,
        evidence_refs=(f"evd:{variant_id}",),
    )


def test_multi_assistant_harness_runs_selected_providers_in_parallel() -> None:
    router = ProviderRouter([FakeProvider("alpha"), FakeProvider("beta")])
    harness = MultiAssistantEvaluationHarness(router)
    runs = asyncio.run(
        harness.run(
            "hello", provider_names=["alpha", "beta"], required_capabilities=["text"]
        )
    )
    assert [run.provider for run in runs] == ["alpha", "beta"]
    assert all(run.success for run in runs)
    assert all(run.output_digest for run in runs)
    assert runs[0].output != runs[1].output


def test_multi_assistant_harness_fails_one_provider_without_aborting_all() -> None:
    router = ProviderRouter([FakeProvider("good"), FakeProvider("bad", fail=True)])
    harness = MultiAssistantEvaluationHarness(router)
    runs = asyncio.run(harness.run("hello", provider_names=["good", "bad"]))
    by_name = {run.provider: run for run in runs}
    assert by_name["good"].success is True
    assert by_name["bad"].success is False
    assert by_name["bad"].error_code == "DEGRADED"


def test_parallel_run_evidence_stores_digest_not_raw_output(tmp_path: Path) -> None:
    router = ProviderRouter([FakeProvider("alpha", "SUPER_SECRET_RESPONSE")])
    runs = asyncio.run(
        MultiAssistantEvaluationHarness(router).run("prompt", provider_names=["alpha"])
    )
    store = ledger(tmp_path)
    experimenter = IdeaAutoExperimenter(store)
    experimenter.record_parallel_runs(
        experiment_id="exp-1", prompt_digest="digest:prompt", runs=runs
    )
    raw = (tmp_path / "experiment.jsonl").read_text(encoding="utf-8")
    assert "SUPER_SECRET_RESPONSE" not in raw
    assert runs[0].output_digest in raw
    assert '"raw_outputs_stored": false' in raw


def test_candidate_can_be_proposed_when_verified_and_materially_better(
    tmp_path: Path,
) -> None:
    experimenter = IdeaAutoExperimenter(ledger(tmp_path), minimum_improvement=0.05)
    outcome = experimenter.evaluate(
        baseline_id="baseline",
        variants=[
            score("baseline", quality=0.55, reliability=0.70, cost_score=0.60),
            score("candidate", quality=0.90, reliability=0.90, cost_score=0.80),
        ],
        hypothesis="candidate is better",
        verified_by="independent_verifier",
    )
    assert outcome.decision is ExperimentDecision.PROMOTION_CANDIDATE
    assert outcome.winner_id == "candidate"
    raw = (tmp_path / "experiment.jsonl").read_text(encoding="utf-8")
    assert '"auto_promote": false' in raw
    assert '"production_mutation": false' in raw
    assert "candidate is better" not in raw


def test_small_improvement_requires_retest(tmp_path: Path) -> None:
    experimenter = IdeaAutoExperimenter(ledger(tmp_path), minimum_improvement=0.20)
    outcome = experimenter.evaluate(
        baseline_id="baseline",
        variants=[
            score("baseline", quality=0.70, reliability=0.80, cost_score=0.70),
            score("candidate", quality=0.75, reliability=0.82, cost_score=0.72),
        ],
        hypothesis="small change",
        verified_by="human_governor",
    )
    assert outcome.decision is ExperimentDecision.RETEST


def test_baseline_winner_rejects_candidate(tmp_path: Path) -> None:
    experimenter = IdeaAutoExperimenter(ledger(tmp_path))
    outcome = experimenter.evaluate(
        baseline_id="baseline",
        variants=[
            score("baseline", quality=0.95, reliability=0.95, cost_score=0.90),
            score("candidate", quality=0.50, reliability=0.60, cost_score=0.50),
        ],
        hypothesis="candidate might improve system",
        verified_by="independent_verifier",
    )
    assert outcome.decision is ExperimentDecision.REJECT
    assert outcome.winner_id is None


@pytest.mark.parametrize("verifier", ["agnes", "self", "model", "assistant", ""])
def test_self_verification_is_rejected(tmp_path: Path, verifier: str) -> None:
    experimenter = IdeaAutoExperimenter(ledger(tmp_path))
    with pytest.raises(PermissionError):
        experimenter.evaluate(
            baseline_id="baseline",
            variants=[
                score("baseline", quality=0.5, reliability=0.5, cost_score=0.5),
                score("candidate", quality=0.9, reliability=0.9, cost_score=0.9),
            ],
            hypothesis="unsafe self approval",
            verified_by=verifier,
        )


def test_missing_evidence_fails_closed(tmp_path: Path) -> None:
    experimenter = IdeaAutoExperimenter(ledger(tmp_path))
    bad = VariantScore("candidate", 0.9, 0.9, 10, 0.9, ())
    with pytest.raises(ValueError, match="requires evidence"):
        experimenter.evaluate(
            baseline_id="baseline",
            variants=[
                score("baseline", quality=0.5, reliability=0.5, cost_score=0.5),
                bad,
            ],
            hypothesis="missing evidence",
            verified_by="human_governor",
        )


def test_ledger_tamper_is_detected(tmp_path: Path) -> None:
    store = ledger(tmp_path)
    store.append("seed", {"ok": True})
    path = tmp_path / "experiment.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace("true", "false"), encoding="utf-8"
    )
    assert store.verify().valid is False
