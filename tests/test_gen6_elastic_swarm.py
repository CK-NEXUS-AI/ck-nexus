from __future__ import annotations

import pytest
from pydantic import ValidationError

from creator_app.core.consensus_engine import (
    AgentVote,
    ConsensusEngine,
    ConsensusRule,
    ConsensusStatus,
    VoteType,
)
from creator_app.core.dynamic_subagent_factory import (
    AgentLifecycle,
    AgentRole,
    AgentSpec,
    DynamicSubagentFactory,
)
from creator_app.core.elastic_swarm_director import (
    ElasticSwarmDirector,
    SwarmStatus,
    SwarmTask,
    WorkerOutcome,
)
from creator_app.core.fanout_fanin_budget import (
    BudgetLevel,
    BudgetPolicy,
    FanoutFaninBudgetController,
)
from creator_app.core.model_pool_selector import (
    ModelPoolSelector,
    ModelRecord,
    ModelRiskLevel,
    ModelSelectionCriteria,
    ModelStatus,
    SelectionStrategy,
)


def _budget_policy(total: float = 10.0, workers: int = 4) -> BudgetPolicy:
    return BudgetPolicy(total_budget=total, max_concurrent_workers=workers)


def _vote(voter_id: str, role: str, vote: VoteType) -> AgentVote:
    return AgentVote(
        voter_id=voter_id,
        role=role,
        vote=vote,
        reason="evidence-backed review",
        evidence_ids=[f"evidence:{voter_id}"],
    )


def _model(
    model_id: str,
    *,
    provider: str,
    cost: float,
    latency: int,
    quality: float,
) -> ModelRecord:
    return ModelRecord(
        model_id=model_id,
        provider=provider,
        capabilities={"reasoning", "research"},
        cost_per_1k_tokens=cost,
        latency_ms=latency,
        quality_score=quality,
        risk_allowed={ModelRiskLevel.LOW, ModelRiskLevel.MEDIUM},
        status=ModelStatus.AVAILABLE,
    )


def test_swarm_initialization_and_start() -> None:
    swarm = ElasticSwarmDirector(swarm_id="swarm-1", budget_policy=_budget_policy())
    assert swarm.status == SwarmStatus.INITIALIZING
    swarm.start()
    assert swarm.status == SwarmStatus.RUNNING


def test_task_decomposition_creates_deterministic_subtasks() -> None:
    swarm = ElasticSwarmDirector(swarm_id="swarm-1", budget_policy=_budget_policy())
    swarm.start()
    tasks = swarm.decompose(
        parent_task_id="mission",
        fragments=["research", "review"],
        estimated_costs=[1.0, 2.0],
    )
    assert [task.task_id for task in tasks] == ["mission:1", "mission:2"]
    assert [task.estimated_cost for task in tasks] == [1.0, 2.0]


def test_dynamic_subagent_creation_and_lifecycle() -> None:
    factory = DynamicSubagentFactory()
    researcher = factory.create_researcher(agent_id="agent-r")
    assert researcher.spec.role == AgentRole.RESEARCHER
    assigned = factory.assign(agent_id="agent-r", task_id="task-1")
    assert assigned.lifecycle == AgentLifecycle.ASSIGNED
    executing = factory.mark_executing(agent_id="agent-r")
    assert executing.lifecycle == AgentLifecycle.EXECUTING
    retired = factory.retire(agent_id="agent-r")
    assert retired.lifecycle == AgentLifecycle.RETIRED
    assert retired.resources_released is True
    with pytest.raises(ValueError, match="retired agent"):
        factory.assign(agent_id="agent-r", task_id="task-2")


def test_model_pool_selection_strategies_and_fallbacks() -> None:
    selector = ModelPoolSelector()
    selector.register(
        _model("cheap", provider="provider-a", cost=0.1, latency=200, quality=0.70)
    )
    selector.register(
        _model("quality", provider="provider-b", cost=0.8, latency=300, quality=0.95)
    )
    selector.register(
        _model("fast", provider="provider-c", cost=0.4, latency=50, quality=0.80)
    )

    cost_pick = selector.select(
        ModelSelectionCriteria(
            required_capabilities={"reasoning"},
            strategy=SelectionStrategy.COST_OPTIMIZED,
        )
    )
    assert cost_pick.primary.model_id == "cheap"
    assert len(cost_pick.fallbacks) == 2

    quality_pick = selector.select(
        ModelSelectionCriteria(
            required_capabilities={"reasoning"},
            strategy=SelectionStrategy.QUALITY_OPTIMIZED,
        )
    )
    assert quality_pick.primary.model_id == "quality"

    latency_pick = selector.select(
        ModelSelectionCriteria(
            required_capabilities={"reasoning"},
            strategy=SelectionStrategy.LATENCY_OPTIMIZED,
        )
    )
    assert latency_pick.primary.model_id == "fast"


def test_model_pool_circuit_breaker_fail_closed() -> None:
    selector = ModelPoolSelector(circuit_breaker_threshold=2)
    selector.register(
        _model("only", provider="provider-a", cost=0.2, latency=100, quality=0.80)
    )
    selector.record_provider_failure("provider-a")
    selector.record_provider_failure("provider-a")
    assert selector.provider_circuit_open("provider-a") is True
    with pytest.raises(LookupError, match="no eligible model"):
        selector.select(ModelSelectionCriteria(required_capabilities={"reasoning"}))


def test_budget_enforcement_and_thresholds() -> None:
    controller = FanoutFaninBudgetController(_budget_policy(total=10.0, workers=2))
    controller.reserve(5.0, active_workers=0)
    assert controller.level == BudgetLevel.WARNING
    controller.settle(reserved_cost=5.0, actual_cost=8.0)
    assert controller.level == BudgetLevel.CRITICAL
    controller.reserve(1.5, active_workers=0)
    assert controller.level == BudgetLevel.EXHAUSTED
    assert controller.cheapest_model_only is True
    with pytest.raises(ValueError, match="budget policy"):
        controller.reserve(1.0, active_workers=1)


def test_fanout_and_fanin_complete_swarm() -> None:
    swarm = ElasticSwarmDirector(
        swarm_id="swarm-1",
        budget_policy=_budget_policy(total=5.0, workers=2),
    )
    swarm.start()
    swarm.add_task(SwarmTask(task_id="t1", description="research", estimated_cost=1.0))
    swarm.add_task(SwarmTask(task_id="t2", description="review", estimated_cost=1.0))
    swarm.assign_worker(task_id="t1", agent_id="a1")
    swarm.assign_worker(task_id="t2", agent_id="a2")
    running = swarm.fan_out(["t1", "t2"])
    assert len(running) == 2
    assert swarm.status == SwarmStatus.SCALING

    swarm.fan_in(
        [
            WorkerOutcome(
                task_id="t1",
                agent_id="a1",
                success=True,
                evidence_ids=["e1"],
                actual_cost=0.8,
            ),
            WorkerOutcome(
                task_id="t2",
                agent_id="a2",
                success=True,
                evidence_ids=["e2"],
                actual_cost=0.9,
            ),
        ]
    )
    snapshot = swarm.snapshot()
    assert snapshot.status == SwarmStatus.COMPLETED
    assert snapshot.completed_tasks == 2
    assert snapshot.failed_tasks == 0


def test_worker_failure_threshold_fails_swarm() -> None:
    swarm = ElasticSwarmDirector(
        swarm_id="swarm-1",
        budget_policy=_budget_policy(),
        max_worker_failures=0,
    )
    swarm.start()
    swarm.add_task(SwarmTask(task_id="t1", description="task", estimated_cost=0.1))
    swarm.assign_worker(task_id="t1", agent_id="a1")
    swarm.fan_out(["t1"])
    swarm.fan_in(
        [
            WorkerOutcome(
                task_id="t1",
                agent_id="a1",
                success=False,
                actual_cost=0.1,
            )
        ]
    )
    assert swarm.status == SwarmStatus.FAILED


def test_success_without_evidence_is_rejected() -> None:
    swarm = ElasticSwarmDirector(swarm_id="swarm-1", budget_policy=_budget_policy())
    swarm.start()
    swarm.add_task(SwarmTask(task_id="t1", description="task", estimated_cost=0.1))
    swarm.assign_worker(task_id="t1", agent_id="a1")
    swarm.fan_out(["t1"])
    with pytest.raises(ValueError, match="requires evidence"):
        swarm.fan_in(
            [
                WorkerOutcome(
                    task_id="t1",
                    agent_id="a1",
                    success=True,
                    actual_cost=0.1,
                )
            ]
        )


def test_consensus_rules_and_escalation() -> None:
    engine = ConsensusEngine()
    accepted = engine.evaluate(
        [
            _vote("v1", "verifier", VoteType.APPROVE),
            _vote("v2", "reviewer", VoteType.APPROVE),
            _vote("v3", "challenger", VoteType.REJECT),
        ],
        rule=ConsensusRule.MAJORITY,
    )
    assert accepted.status == ConsensusStatus.ACCEPTED

    unanimous_reject = engine.evaluate(
        [
            _vote("v1", "verifier", VoteType.APPROVE),
            _vote("v2", "challenger", VoteType.REJECT),
        ],
        rule=ConsensusRule.UNANIMOUS,
    )
    assert unanimous_reject.status == ConsensusStatus.REJECTED

    escalated = engine.evaluate(
        [
            _vote("v1", "reviewer", VoteType.APPROVE),
            _vote("v2", "challenger", VoteType.REJECT),
        ],
        rule=ConsensusRule.MAJORITY,
    )
    assert escalated.status == ConsensusStatus.ESCALATED


def test_weighted_consensus_gives_verifier_more_weight() -> None:
    decision = ConsensusEngine().evaluate(
        [
            _vote("verifier", "verifier", VoteType.REJECT),
            _vote("scout-1", "scout", VoteType.APPROVE),
            _vote("scout-2", "scout", VoteType.APPROVE),
        ],
        rule=ConsensusRule.WEIGHTED,
    )
    assert decision.status == ConsensusStatus.REJECTED


def test_fail_closed_missing_model_budget_and_invalid_agent() -> None:
    selector = ModelPoolSelector()
    with pytest.raises(LookupError, match="no eligible model"):
        selector.select(ModelSelectionCriteria(required_capabilities={"vision"}))

    budget = FanoutFaninBudgetController(_budget_policy(total=1.0, workers=1))
    with pytest.raises(ValueError, match="budget policy"):
        budget.reserve(1.1, active_workers=0)

    factory = DynamicSubagentFactory()
    with pytest.raises(KeyError, match="unknown agent"):
        factory.assign(agent_id="missing", task_id="task")


def test_invalid_role_and_invalid_vote_are_rejected_by_schema() -> None:
    with pytest.raises(ValidationError):
        AgentSpec(
            agent_id="bad-agent",
            role="not-a-role",
            capabilities=set(),
            context_id="context:bad-agent",
        )

    with pytest.raises(ValidationError):
        AgentVote(
            voter_id="bad-vote",
            role="reviewer",
            vote="not-a-vote",
            reason="invalid",
            evidence_ids=["evidence:bad"],
        )
