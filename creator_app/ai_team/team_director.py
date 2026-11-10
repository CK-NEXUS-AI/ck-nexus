"""TeamDirector — หัวหน้าทีม ผู้ประสานงานหลัก.

สั่งงานครั้งเดียว → ทีมทำงานเองทั้งหมด
- แบ่งงาน
- ตรวจ
- รวมผล
- บันทึกประวัติ
"""

from __future__ import annotations

import asyncio
import math
import os
import threading
import time
from copy import deepcopy
from typing import Any

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    TaskResult,
    TaskStatus,
    TeamPlan,
    TeamRequest,
    TeamResult,
    generate_id,
)
from creator_app.ai_team.agents import (
    AnalystAgent,
    ConnectorAgent,
    DesignerAgent,
    DirectorAgent,
    EngineerAgent,
    GuardianAgent,
    ResearcherAgent,
)
from creator_app.ai_team.auto_response import AgentMessage, AgentMessageBus
from creator_app.ai_team.intelligence.parallel_executor import (
    ParallelExecutor,
)
from creator_app.ai_team.intelligence.parallel_executor import (
    TaskStatus as ParallelTaskStatus,
)
from creator_app.ai_team.shared_knowledge import SharedKnowledge
from creator_app.development_control import (
    DevelopmentStatusStore,
    default_development_status_db_path,
)


class TeamDirector:
    """หัวหน้าทีม — สร้างทีม วางแผน แบ่งงาน ประสานงาน รวมผล.

    วิธีใช้:
        team = TeamDirector()
        result = team.process_request("สร้างระบบเชื่อม Gmail")
        print(result.final_output)
    """

    def __init__(
        self,
        knowledge_path: str | None = None,
        development_status_path: str | None = None,
        *,
        max_concurrency: int = 2,
        step_timeout: float = 60.0,
    ) -> None:
        if (
            isinstance(max_concurrency, bool)
            or not isinstance(max_concurrency, int)
            or not 1 <= max_concurrency <= 5
        ):
            raise ValueError("max_concurrency must be an integer between 1 and 5")
        if (
            isinstance(step_timeout, bool)
            or not isinstance(step_timeout, (int, float))
            or not math.isfinite(step_timeout)
            or step_timeout <= 0
        ):
            raise ValueError("step_timeout must be a positive finite number")
        self.max_concurrency = max_concurrency
        self.step_timeout = float(step_timeout)
        self.director = DirectorAgent()
        self.agents: dict[str, Agent] = {
            "engineer": EngineerAgent(),
            "guardian": GuardianAgent(),
            "analyst": AnalystAgent(),
            "researcher": ResearcherAgent(),
            "designer": DesignerAgent(),
            "connector": ConnectorAgent(),
        }
        self.knowledge = SharedKnowledge(persistence_path=knowledge_path)
        self.message_bus = AgentMessageBus(max_hops=4, max_history=500)
        for agent_name, agent in self.agents.items():
            self._register_auto_responder(agent_name, agent)
        self._development_status_path = development_status_path or os.environ.get(
            "CKNEXUS_DEVELOPMENT_STATUS_DB",
            str(default_development_status_db_path()),
        )
        self._request_history: list[TeamResult] = []

    def process_request(
        self,
        description: str,
        *,
        priority: int = 2,
        context: str = "",
        constraints: tuple[str, ...] = (),
    ) -> TeamResult:
        """Synchronous compatibility entry point for non-async callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.aprocess_request(
                    description,
                    priority=priority,
                    context=context,
                    constraints=constraints,
                )
            )
        raise RuntimeError(
            "process_request cannot run inside an active event loop; "
            "use await aprocess_request(...) instead"
        )

    async def aprocess_request(
        self,
        description: str,
        *,
        priority: int = 2,
        context: str = "",
        constraints: tuple[str, ...] = (),
    ) -> TeamResult:
        """Asynchronous TeamDirector entry point."""
        start = time.time()

        from creator_app.ai_team.agent_models import RequestPriority

        request = TeamRequest(
            request_id=generate_id("req"),
            description=description,
            priority=RequestPriority(priority),
            context=context,
            constraints=constraints,
        )

        existing_knowledge = self.knowledge.search(description, max_results=3)
        knowledge_context = ""
        if existing_knowledge:
            knowledge_context = "\n".join(
                f"ความรู้เดิม ({item.topic}): {item.content[:200]}"
                for item in existing_knowledge
            )

        plan_result = await asyncio.to_thread(
            self.director.process,
            request,
            context={"agents": list(self.agents.values())},
        )
        plan = plan_result.metadata.get("plan")
        if plan is None:
            plan = TeamPlan(request_id=request.request_id)

        step_results = await self._execute_plan_waves(request, plan, knowledge_context)

        synthesis = await asyncio.to_thread(
            self.director.synthesize_results, step_results, request
        )

        team_result = TeamResult(
            request_id=request.request_id,
            final_output=synthesis.output,
            status=TaskStatus.COMPLETED,
            steps_completed=len(step_results),
            steps_total=plan.total_steps,
            team_members_used=tuple(dict.fromkeys(result.agent_name for result in step_results)),
            duration_seconds=time.time() - start,
            artifacts=tuple(
                artifact for result in step_results for artifact in result.artifacts
            ),
            confidence=synthesis.confidence,
            plan=plan,
            step_results=step_results,
        )

        self._request_history.append(team_result)
        return team_result

    async def _execute_plan_waves(
        self,
        request: TeamRequest,
        plan: TeamPlan,
        knowledge_context: str,
    ) -> list[TaskResult]:
        """Run dependency-ready plan steps in bounded waves."""
        steps = list(plan.steps)
        step_ids = [step.step_id for step in steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("plan contains duplicate step IDs")

        order = {step_id: index for index, step_id in enumerate(step_ids)}
        pending = {step.step_id: step for step in steps}
        completed_ids: set[str] = set()
        failed_ids: set[str] = set()
        blocked_ids: set[str] = set()
        results_by_id: dict[str, TaskResult] = {}
        executor = ParallelExecutor(max_concurrency=self.max_concurrency)
        agent_locks: dict[int, threading.Lock] = {}
        wave_number = 0

        def record_blocked(step: Any, reason: str) -> None:
            result = TaskResult(
                task_id=step.step_id,
                agent_name=step.agent_name,
                agent_role=step.agent_role,
                status=TaskStatus.BLOCKED,
                output=reason,
                warnings=(reason,),
            )
            step.status = TaskStatus.BLOCKED
            blocked_ids.add(step.step_id)
            results_by_id[step.step_id] = result
            pending.pop(step.step_id, None)

        while pending:
            for step in list(pending.values()):
                unknown_dependencies = set(step.depends_on) - set(order)
                if unknown_dependencies:
                    missing = ", ".join(sorted(unknown_dependencies))
                    record_blocked(step, f"unknown dependencies: {missing}")
                elif set(step.depends_on) & (failed_ids | blocked_ids):
                    record_blocked(step, "blocked by a failed or blocked dependency")

            ready = [
                step
                for step in pending.values()
                if set(step.depends_on).issubset(completed_ids)
            ]
            if not ready:
                for step in list(pending.values()):
                    record_blocked(step, "dependency cycle or no runnable predecessor path")
                break

            executable: list[tuple[Any, Agent]] = []
            for step in ready:
                agent = self.agents.get(step.agent_role)
                if agent is None:
                    reason = f"no agent registered for role: {step.agent_role}"
                    result = TaskResult(
                        task_id=step.step_id,
                        agent_name=step.agent_name,
                        agent_role=step.agent_role,
                        status=TaskStatus.FAILED,
                        output=reason,
                        warnings=(reason,),
                    )
                    step.status = TaskStatus.FAILED
                    failed_ids.add(step.step_id)
                    results_by_id[step.step_id] = result
                    pending.pop(step.step_id, None)
                else:
                    executable.append((step, agent))

            if not executable:
                continue

            wave_number += 1
            prior_results = [
                results_by_id[step.step_id]
                for step in steps
                if step.step_id in results_by_id
            ]
            completed_snapshot = frozenset(completed_ids)
            tasks = []
            agents_by_step: dict[str, Agent] = {}

            for step, agent in executable:
                agents_by_step[step.step_id] = agent
                agent_lock = agent_locks.setdefault(id(agent), threading.Lock())

                def invoke(
                    selected_agent: Agent = agent,
                    selected_lock: threading.Lock = agent_lock,
                    completed_steps_snapshot: frozenset[str] = completed_snapshot,
                    prior_step_results: list[TaskResult] = prior_results,
                ) -> TaskResult:
                    worker_request = deepcopy(request)
                    worker_plan = deepcopy(plan)
                    worker_context = {
                        "request": worker_request,
                        "plan": worker_plan,
                        "completed_steps": completed_steps_snapshot,
                        "step_results": deepcopy(prior_step_results),
                        "knowledge_context": knowledge_context,
                    }
                    with selected_lock:
                        return selected_agent.process(worker_request, context=worker_context)

                tasks.append((step.step_id, invoke))

            batch_results = await executor.run_batch(
                f"{request.request_id}-wave-{wave_number}",
                tasks,
                timeout=self.step_timeout,
            )

            for batch_result in batch_results:
                step = pending[batch_result.task_id]
                agent = agents_by_step[step.step_id]
                result = batch_result.result
                if (
                    batch_result.status is ParallelTaskStatus.COMPLETED
                    and isinstance(result, TaskResult)
                    and result.status
                    in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED}
                ):
                    integrated_result = result
                else:
                    error = batch_result.error or "agent returned an invalid or non-terminal result"
                    integrated_result = TaskResult(
                        task_id=step.step_id,
                        agent_name=agent.name,
                        agent_role=step.agent_role,
                        status=TaskStatus.FAILED,
                        output=f"agent execution failed: {error}",
                        warnings=(error,),
                    )

                step.status = integrated_result.status
                if integrated_result.status is TaskStatus.COMPLETED:
                    completed_ids.add(step.step_id)
                    self.knowledge.add(
                        topic=request.description[:100],
                        agent_name=agent.name,
                        content=integrated_result.output,
                        keywords=tuple(request.description.lower().split()[:5]),
                        confidence=integrated_result.confidence,
                    )
                elif integrated_result.status is TaskStatus.BLOCKED:
                    blocked_ids.add(step.step_id)
                else:
                    failed_ids.add(step.step_id)

                agent.record_result(integrated_result)
                results_by_id[step.step_id] = integrated_result
                pending.pop(step.step_id, None)

        return [results_by_id[step.step_id] for step in steps if step.step_id in results_by_id]

    def list_team(self) -> dict[str, Any]:
        members = []
        members.append(
            {
                "name": self.director.name,
                "role": self.director.role.value,
                "description": self.director.description,
                "expertise": list(self.director.expertise),
            }
        )
        for agent in self.agents.values():
            members.append(
                {
                    "name": agent.name,
                    "role": agent.role.value,
                    "description": agent.description,
                    "expertise": list(agent.expertise),
                }
            )
        return {
            "team_name": "CK-NEXUS AI Expert Team",
            "total_members": len(members),
            "members": members,
        }

    def team_status(self) -> dict[str, Any]:
        agent_statuses = [self.director.status()]
        agent_statuses.extend(a.status() for a in self.agents.values())
        return {
            "team_name": "CK-NEXUS AI Expert Team",
            "total_requests": len(self._request_history),
            "knowledge_stats": self.knowledge.stats(),
            "agents": agent_statuses,
        }

    def admit_agent(
        self,
        name: str,
        agent: Agent,
        *,
        competency_agent_id: str,
    ) -> None:
        """Admit a dynamic development AI only after the competency gate."""
        store = DevelopmentStatusStore(self._development_status_path)
        try:
            store.require_write_authority(competency_agent_id)
        except KeyError as exc:
            store.record_agent_admission(
                agent_id=competency_agent_id,
                team_key=name,
                admitted=False,
                reason="competency_assessment_missing",
            )
            raise PermissionError("dynamic development agent has no competency assessment") from exc
        except PermissionError as exc:
            store.record_agent_admission(
                agent_id=competency_agent_id,
                team_key=name,
                admitted=False,
                reason="pro_level_write_authority_required",
            )
            raise PermissionError(
                "dynamic development agent requires human-confirmed PRO_LEVEL"
            ) from exc

        self.agents[name] = agent
        self._register_auto_responder(name, agent)
        store.record_agent_admission(
            agent_id=competency_agent_id,
            team_key=name,
            admitted=True,
            reason="human_confirmed_pro_level",
        )

    def _register_auto_responder(self, name: str, agent: Agent) -> None:
        """Register a bounded request/response adapter for one team member."""

        def respond(message: AgentMessage) -> str:
            from creator_app.ai_team.agent_models import RequestPriority

            request = TeamRequest(
                request_id=message.correlation_id,
                description=message.content,
                priority=RequestPriority.NORMAL,
                context=f"Automated peer request from {message.sender}",
                metadata={"conversation_id": message.conversation_id},
            )
            result = agent.process(request, context={"message": message.as_dict()})
            agent.record_result(result)
            return result.output

        self.message_bus.register(name, respond)

    def send_agent_message(
        self,
        *,
        sender: str,
        recipient: str,
        content: str,
        idempotency_key: str | None = None,
    ) -> AgentMessage:
        """Send a peer request and return its automatic response."""
        return self.message_bus.request(
            sender=sender,
            recipient=recipient,
            content=content,
            idempotency_key=idempotency_key,
        )

    def add_agent(self, name: str, agent: Agent) -> None:
        """Internal/bootstrap compatibility path; external AI must use admit_agent."""
        self.agents[name] = agent
        self._register_auto_responder(name, agent)

    def remove_agent(self, name: str) -> bool:
        if name in self.agents:
            del self.agents[name]
            self.message_bus.unregister(name)
            return True
        return False

    def get_history(self) -> list[TeamResult]:
        return list(self._request_history)
