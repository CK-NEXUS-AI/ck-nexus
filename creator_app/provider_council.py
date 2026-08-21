from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable, Mapping

from creator_app.agnes_idea_experimenter import AssistantRun, MultiAssistantEvaluationHarness
from creator_app.agnes_ledger import AppendOnlyLedger
from creator_app.provider_router import ProviderKind, ProviderRouter


class CouncilMode(StrEnum):
    PARALLEL = "parallel"
    CONSENSUS = "consensus"
    ADVERSARIAL = "adversarial"
    FAST = "fast"
    CHEAP = "cheap"
    DEEP = "deep"


class CouncilDecision(StrEnum):
    COMPLETE = "complete"
    QUORUM_FAILED = "quorum_failed"
    NEEDS_VERIFICATION = "needs_verification"


@dataclass(frozen=True, slots=True)
class CouncilPolicy:
    max_parallel: int = 5
    minimum_quorum: int = 2

    def __post_init__(self) -> None:
        if self.max_parallel < 1:
            raise ValueError("max_parallel must be at least 1")
        if self.minimum_quorum < 1:
            raise ValueError("minimum_quorum must be at least 1")
        if self.minimum_quorum > self.max_parallel:
            raise ValueError("minimum_quorum cannot exceed max_parallel")


@dataclass(frozen=True, slots=True)
class CouncilOutcome:
    mode: CouncilMode
    decision: CouncilDecision
    runs: tuple[AssistantRun, ...]
    quorum: int
    successful: int
    selected_output_digest: str | None
    evidence_ref: str


class ProviderCouncil:
    """Governed multi-provider orchestration above ProviderRouter.

    Credentials remain inside provider adapters. Raw model outputs are returned to
    the caller but never written to the evidence ledger by this class.
    """

    def __init__(
        self,
        router: ProviderRouter,
        ledger: AppendOnlyLedger,
        *,
        policy: CouncilPolicy | None = None,
        provider_cost_rank: Mapping[str, int] | None = None,
    ) -> None:
        self.router = router
        self.ledger = ledger
        self.policy = policy or CouncilPolicy()
        self.harness = MultiAssistantEvaluationHarness(router)
        self.provider_cost_rank = dict(provider_cost_rank or {})

    @staticmethod
    def _digest(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _eligible(
        self,
        required_capabilities: Iterable[str],
        provider_names: Iterable[str] | None,
    ) -> list[str]:
        required = frozenset(required_capabilities)
        requested = None
        if provider_names is not None:
            requested = {name.strip() for name in provider_names if name.strip()}
        rows = []
        for status in self.router.statuses():
            if requested is not None and status.name not in requested:
                continue
            if not status.available or status.circuit_open:
                continue
            if not status.capabilities.supports(required):
                continue
            rows.append(status.name)
        return rows

    def _cost_rank(self, provider_name: str) -> tuple[int, int]:
        explicit = self.provider_cost_rank.get(provider_name)
        if explicit is not None:
            return explicit, 0
        status = next(row for row in self.router.statuses() if row.name == provider_name)
        default = 0 if status.kind in {ProviderKind.LOCAL, ProviderKind.MOCK} else 100
        return default, 1

    async def execute(
        self,
        prompt: str,
        *,
        mode: CouncilMode,
        provider_names: Iterable[str] | None = None,
        required_capabilities: Iterable[str] = (),
    ) -> CouncilOutcome:
        names = self._eligible(required_capabilities, provider_names)
        if not names:
            raise RuntimeError("no eligible providers for council execution")

        quorum = 1 if mode in {CouncilMode.FAST, CouncilMode.CHEAP} else self.policy.minimum_quorum
        if mode is CouncilMode.FAST:
            selected = names[:1]
        elif mode is CouncilMode.CHEAP:
            selected = [min(names, key=self._cost_rank)]
        else:
            selected = names[: self.policy.max_parallel]

        runs = await self.harness.run(
            prompt,
            provider_names=selected,
            required_capabilities=required_capabilities,
        )
        successful_runs = tuple(row for row in runs if row.success)
        successful = len(successful_runs)
        selected_digest: str | None = None

        if successful < quorum:
            decision = CouncilDecision.QUORUM_FAILED
        elif mode is CouncilMode.CONSENSUS:
            counts = Counter(row.output_digest for row in successful_runs if row.output_digest)
            digest, count = counts.most_common(1)[0]
            if count >= quorum:
                selected_digest = digest
                decision = CouncilDecision.COMPLETE
            else:
                decision = CouncilDecision.NEEDS_VERIFICATION
        elif mode is CouncilMode.ADVERSARIAL:
            decision = CouncilDecision.NEEDS_VERIFICATION
        else:
            decision = CouncilDecision.COMPLETE
            if successful == 1:
                selected_digest = successful_runs[0].output_digest

        event = self.ledger.append(
            "provider_council_executed",
            {
                "mode": mode.value,
                "prompt_digest": self._digest(prompt),
                "requested_providers": list(provider_names or ()),
                "selected_providers": selected,
                "required_capabilities": list(required_capabilities),
                "quorum": quorum,
                "successful": successful,
                "decision": decision.value,
                "selected_output_digest": selected_digest,
                "runs": [row.evidence_dict() for row in runs],
                "raw_outputs_stored": False,
                "self_approval": False,
                "auto_promote": False,
                "production_mutation": False,
            },
        )
        evidence_ref = str(event.get("hash") or "")
        if not evidence_ref:
            raise RuntimeError("provider council evidence was not sealed")
        return CouncilOutcome(
            mode=mode,
            decision=decision,
            runs=runs,
            quorum=quorum,
            successful=successful,
            selected_output_digest=selected_digest,
            evidence_ref=evidence_ref,
        )
