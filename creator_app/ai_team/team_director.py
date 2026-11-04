"""TeamDirector — หัวหน้าทีม ผู้ประสานงานหลัก.

สั่งงานครั้งเดียว → ทีมทำงานเองทั้งหมด
- แบ่งงาน
- ตรวจ
- รวมผล
- บันทึกประวัติ
"""

from __future__ import annotations

import os
import time
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
    ) -> None:
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
        """สั่งงานทั้งทีม — ครั้งเดียวจบทั้งระบบ."""
        start = time.time()

        from creator_app.ai_team.agent_models import RequestPriority

        request = TeamRequest(
            request_id=generate_id("req"),
            description=description,
            priority=RequestPriority(priority),
            context=context,
            constraints=constraints,
        )

        # ค้นหาความรู้เดิม
        existing_knowledge = self.knowledge.search(description, max_results=3)
        knowledge_context = ""
        if existing_knowledge:
            knowledge_context = "\n".join(
                f"ความรู้เดิม ({k.topic}): {k.content[:200]}" for k in existing_knowledge
            )

        # Director วางแผน
        plan_result = self.director.process(
            request,
            context={"agents": list(self.agents.values())},
        )
        plan = plan_result.metadata.get("plan")
        if plan is None:
            plan = TeamPlan(request_id=request.request_id)

        # ทำงานตามแผน
        step_results: list[TaskResult] = []
        completed_steps: set[str] = set()

        for step in plan.steps:
            deps_met = all(d in completed_steps for d in step.depends_on)
            if not deps_met:
                continue

            agent = self.agents.get(step.agent_role)
            if agent is None:
                continue

            agent_context = {
                "request": request,
                "plan": plan,
                "completed_steps": completed_steps,
                "step_results": step_results,
                "knowledge_context": knowledge_context,
            }

            result = agent.process(request, context=agent_context)
            agent.record_result(result)
            step_results.append(result)
            completed_steps.add(step.step_id)

            if result.status == TaskStatus.COMPLETED:
                self.knowledge.add(
                    topic=description[:100],
                    agent_name=agent.name,
                    content=result.output,
                    keywords=tuple(description.lower().split()[:5]),
                    confidence=result.confidence,
                )

        # Director รวมผล
        synthesis = self.director.synthesize_results(step_results, request)

        team_result = TeamResult(
            request_id=request.request_id,
            final_output=synthesis.output,
            status=TaskStatus.COMPLETED,
            steps_completed=len(step_results),
            steps_total=plan.total_steps,
            team_members_used=tuple(dict.fromkeys(r.agent_name for r in step_results)),
            duration_seconds=time.time() - start,
            artifacts=tuple(a for r in step_results for a in r.artifacts),
            confidence=synthesis.confidence,
            plan=plan,
            step_results=step_results,
        )

        self._request_history.append(team_result)
        return team_result

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
