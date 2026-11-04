"""Fail-closed deterministic policy for CK-NEXUS cognitive orchestration."""

from __future__ import annotations

from .contracts import (
    ActionClass,
    CognitiveDecision,
    CognitiveRequest,
    ExecutionMode,
    PlanNode,
    RiskLevel,
)


class CognitiveGovernor:
    """Decide risk, approval, team and orchestration mode before any worker executes."""

    def decide(self, request: CognitiveRequest) -> CognitiveDecision:
        risk = self._risk(request.action_class)
        mode = self._mode(request)
        team = self._team(request)
        nodes = self._nodes(request, team)
        approval_required = request.action_class in {
            ActionClass.EXTERNAL_WRITE,
            ActionClass.DESTRUCTIVE,
            ActionClass.PRODUCTION_MUTATION,
        }

        if request.safety_veto:
            return CognitiveDecision(
                allowed=False,
                risk=RiskLevel.CRITICAL,
                mode=mode,
                approval_required=True,
                reason="blocked_by_independent_safety_veto",
                team=team,
                nodes=nodes,
            )

        if (
            request.action_class == ActionClass.PRODUCTION_MUTATION
            and (not request.user_approved or not request.production_authorized)
        ):
            return CognitiveDecision(
                allowed=False,
                risk=risk,
                mode=mode,
                approval_required=True,
                reason="production_mutation_requires_user_and_release_authority",
                team=team,
                nodes=nodes,
            )

        if (
            request.action_class in {ActionClass.EXTERNAL_WRITE, ActionClass.DESTRUCTIVE}
            and not request.user_approved
        ):
            return CognitiveDecision(
                allowed=False,
                risk=risk,
                mode=mode,
                approval_required=True,
                reason="explicit_user_approval_required",
                team=team,
                nodes=nodes,
            )

        return CognitiveDecision(
            allowed=True,
            risk=risk,
            mode=mode,
            approval_required=approval_required,
            reason="policy_allows_planning_or_execution",
            team=team,
            nodes=nodes,
        )

    @staticmethod
    def _risk(action: ActionClass) -> RiskLevel:
        return {
            ActionClass.READ: RiskLevel.LOW,
            ActionClass.ANALYZE: RiskLevel.LOW,
            ActionClass.DRAFT: RiskLevel.MEDIUM,
            ActionClass.EXTERNAL_WRITE: RiskLevel.HIGH,
            ActionClass.DESTRUCTIVE: RiskLevel.CRITICAL,
            ActionClass.PRODUCTION_MUTATION: RiskLevel.CRITICAL,
        }[action]

    @staticmethod
    def _mode(request: CognitiveRequest) -> ExecutionMode:
        if "shadow" in request.tags:
            return ExecutionMode.SHADOW
        if "architecture" in request.tags and request.budget_tier >= 3:
            return ExecutionMode.DEBATE
        if "security" in request.tags or request.complexity >= 4:
            return ExecutionMode.COUNCIL
        if request.complexity >= 3 and request.budget_tier >= 2:
            return ExecutionMode.PARALLEL
        if request.complexity >= 2:
            return ExecutionMode.FALLBACK
        return ExecutionMode.SINGLE

    @staticmethod
    def _team(request: CognitiveRequest) -> tuple[str, ...]:
        roles: list[str] = ["director"]
        capabilities = request.required_capabilities
        if "research" in request.tags or "research" in capabilities:
            roles.extend(("researcher", "analyst"))
        if "design" in request.tags or "ui" in capabilities:
            roles.append("designer")
        if "code" in capabilities or "build" in request.tags:
            roles.append("engineer")
        if "connector" in capabilities or "integration" in request.tags:
            roles.append("connector")
        if "security" in request.tags or request.action_class in {
            ActionClass.EXTERNAL_WRITE,
            ActionClass.DESTRUCTIVE,
            ActionClass.PRODUCTION_MUTATION,
        }:
            roles.append("guardian")
        roles.append("independent_verifier")
        return tuple(dict.fromkeys(roles))

    @staticmethod
    def _nodes(request: CognitiveRequest, team: tuple[str, ...]) -> tuple[PlanNode, ...]:
        nodes: list[PlanNode] = [PlanNode("node-plan", "director", "plan")]
        worker_ids: list[str] = []
        for index, role in enumerate(team):
            if role in {"director", "independent_verifier"}:
                continue
            node_id = f"node-worker-{index}"
            capability = next(iter(sorted(request.required_capabilities)), "analyze")
            nodes.append(
                PlanNode(
                    node_id=node_id,
                    role=role,
                    capability=capability,
                    dependencies=("node-plan",),
                )
            )
            worker_ids.append(node_id)
        dependencies = tuple(worker_ids) or ("node-plan",)
        nodes.append(
            PlanNode(
                node_id="node-verify",
                role="independent_verifier",
                capability="verify",
                dependencies=dependencies,
                independently_verified=True,
            )
        )
        return tuple(nodes)
