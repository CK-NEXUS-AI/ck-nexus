from __future__ import annotations

import asyncio
import threading
import time

import pytest

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    AgentRole,
    PlanStep,
    TaskResult,
    TaskStatus,
    TeamPlan,
)
from creator_app.ai_team.shared_knowledge import SharedKnowledge
from creator_app.ai_team.team_director import TeamDirector


class _ConcurrencyProbe:
    def __init__(self):
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.events = []

    def run(self, name: str, delay: float = 0.08) -> None:
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.events.append((name, "start", time.monotonic()))
        time.sleep(delay)
        with self.lock:
            self.events.append((name, "end", time.monotonic()))
            self.active -= 1


class _PlannedDirector:
    def __init__(self, plan: TeamPlan):
        self.plan = plan

    def process(self, request, context=None):
        return TaskResult(
            task_id="director-plan",
            agent_name="Director",
            agent_role="director",
            status=TaskStatus.COMPLETED,
            output="plan created",
            metadata={"plan": self.plan},
        )

    def synthesize_results(self, step_results, request):
        return TaskResult(
            task_id="director-synthesis",
            agent_name="Director",
            agent_role="director",
            status=TaskStatus.COMPLETED,
            output="synthesized",
            confidence=0.9,
        )


class _ProbeAgent(Agent):
    def __init__(self, name: str, role: str, probe: _ConcurrencyProbe):
        super().__init__(name=name, role=AgentRole.RESEARCHER, expertise=(role,))
        self.role_name = role
        self.probe = probe

    def process(self, request, context=None):
        self.probe.run(self.role_name)
        return TaskResult(
            task_id=f"result-{self.role_name}",
            agent_name=self.name,
            agent_role=self.role_name,
            status=TaskStatus.COMPLETED,
            output=self.role_name,
        )


def _planned_team(
    steps: list[PlanStep], *, max_concurrency: int = 2, step_timeout: float = 60.0
):
    probe = _ConcurrencyProbe()
    plan = TeamPlan(request_id="planned-request", steps=steps, total_steps=len(steps))
    team = TeamDirector(max_concurrency=max_concurrency, step_timeout=step_timeout)
    team.director = _PlannedDirector(plan)
    team.agents = {
        step.agent_role: _ProbeAgent(step.agent_name, step.agent_role, probe)
        for step in steps
    }
    return team, probe


class TestTeamDirector:
    """ทดสอบ TeamDirector — หัวหน้าทีม."""

    @pytest.mark.parametrize("max_concurrency", [0, 6])
    def test_rejects_out_of_range_concurrency(self, max_concurrency):
        with pytest.raises(ValueError, match="max_concurrency"):
            TeamDirector(max_concurrency=max_concurrency)

    @pytest.mark.parametrize("max_concurrency", [1, 2])
    def test_accepts_bounded_concurrency(self, max_concurrency):
        team = TeamDirector(max_concurrency=max_concurrency)
        assert team.max_concurrency == max_concurrency

    @pytest.mark.parametrize("step_timeout", [0, -1])
    def test_rejects_non_positive_step_timeout(self, step_timeout):
        with pytest.raises(ValueError, match="step_timeout"):
            TeamDirector(step_timeout=step_timeout)

    def test_create_team(self):
        """สร้างทีมได้ 7 คน."""
        team = TeamDirector()
        info = team.list_team()
        assert info["total_members"] == 7
        names = [m["name"] for m in info["members"]]
        assert "Director" in names
        assert "Engineer" in names
        assert "Guardian" in names
        assert "Analyst" in names
        assert "Researcher" in names
        assert "Designer" in names
        assert "Connector" in names

    def test_async_process_request(self):
        team = TeamDirector()

        async def run():
            return await team.aprocess_request("สร้างระบบเขียนโค้ด API")

        result = asyncio.run(run())
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed > 0

    def test_sync_process_request_rejects_running_event_loop(self):
        team = TeamDirector()

        async def run():
            with pytest.raises(RuntimeError, match="aprocess_request"):
                team.process_request("สร้างระบบเขียนโค้ด API")

        asyncio.run(run())

    def test_parallel_execution_overlaps_independent_steps(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "independent A"),
            PlanStep("step-b", "Agent B", "b", "independent B"),
        ]
        team, probe = _planned_team(steps)

        result = asyncio.run(team.aprocess_request("parallel work"))

        assert result.steps_completed == 2
        assert probe.max_active == 2

    def test_parallel_execution_respects_concurrency_limit(self):
        steps = [
            PlanStep(f"step-{name}", f"Agent {name}", name, f"independent {name}")
            for name in ("a", "b", "c", "d", "e")
        ]
        team, probe = _planned_team(steps, max_concurrency=2)

        result = asyncio.run(team.aprocess_request("bounded parallel work"))

        assert result.steps_completed == 5
        assert probe.max_active == 2
        assert probe.max_active <= team.max_concurrency

    def test_shared_agent_instance_is_serialized(self):
        steps = [
            PlanStep("step-a", "Shared Agent", "a", "first task"),
            PlanStep("step-b", "Shared Agent", "b", "second task"),
        ]
        team, probe = _planned_team(steps)
        shared_agent = _ProbeAgent("Shared Agent", "shared", probe)
        team.agents = {"a": shared_agent, "b": shared_agent}

        result = asyncio.run(team.aprocess_request("shared agent safety"))

        assert result.steps_completed == 2
        assert probe.max_active == 1

    def test_dependent_steps_wait_for_successful_dependencies(self):
        steps = [
            PlanStep(
                "step-final", "Final Agent", "final", "combine results",
                depends_on=("step-a", "step-b"),
            ),
            PlanStep("step-a", "Agent A", "a", "independent A"),
            PlanStep("step-b", "Agent B", "b", "independent B"),
        ]
        team, probe = _planned_team(steps)

        result = asyncio.run(team.aprocess_request("dependency wave work"))

        assert {item.task_id for item in result.step_results} == {
            "result-a",
            "result-b",
            "result-final",
        }
        end_times = {
            name: timestamp for name, event, timestamp in probe.events if event == "end"
        }
        final_start = next(
            timestamp for name, event, timestamp in probe.events
            if name == "final" and event == "start"
        )
        assert end_times["a"] < final_start
        assert end_times["b"] < final_start

    def test_parallel_results_follow_plan_order(self):
        steps = [
            PlanStep("step-b", "Agent B", "b", "slower B"),
            PlanStep("step-a", "Agent A", "a", "faster A"),
        ]
        team, probe = _planned_team(steps)

        class TimedAgent(_ProbeAgent):
            def process(self, request, context=None):
                delay = 0.15 if self.role_name == "b" else 0.02
                self.probe.run(self.role_name, delay=delay)
                return TaskResult(
                    task_id=f"result-{self.role_name}",
                    agent_name=self.name,
                    agent_role=self.role_name,
                    status=TaskStatus.COMPLETED,
                    output=self.role_name,
                )

        team.agents = {
            step.agent_role: TimedAgent(step.agent_name, step.agent_role, probe)
            for step in steps
        }

        result = asyncio.run(team.aprocess_request("ordered results"))

        assert [item.task_id for item in result.step_results] == ["result-b", "result-a"]
        end_times = {
            name: timestamp for name, event, timestamp in probe.events if event == "end"
        }
        assert end_times["a"] < end_times["b"]

    def test_parallel_workers_receive_isolated_context_snapshots(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "mutates its private context"),
            PlanStep("step-b", "Agent B", "b", "observes its private context"),
        ]
        team, probe = _planned_team(steps)
        barrier = threading.Barrier(2)
        observed = {}

        class ContextAgent(_ProbeAgent):
            def process(self, request, context=None):
                barrier.wait(timeout=1)
                if self.role_name == "a":
                    context["step_results"].append("private mutation")
                    context["plan"].steps[0].description = "private plan mutation"
                    context["request"].description = "private request mutation"
                    output = "mutated private copy"
                else:
                    observed["request"] = request.description
                    observed["plan"] = context["plan"].steps[0].description
                    observed["results"] = list(context["step_results"])
                    observed["completed"] = context["completed_steps"]
                    output = "observed isolated copy"
                return TaskResult(
                    task_id=f"result-{self.role_name}",
                    agent_name=self.name,
                    agent_role=self.role_name,
                    status=TaskStatus.COMPLETED,
                    output=output,
                )

        team.agents = {
            step.agent_role: ContextAgent(step.agent_name, step.agent_role, probe)
            for step in steps
        }
        result = asyncio.run(team.aprocess_request("original request"))

        assert result.steps_completed == 2
        assert observed["request"] == "original request"
        assert observed["plan"] == "mutates its private context"
        assert observed["results"] == []
        assert observed["completed"] == frozenset()

    def test_empty_plan_is_not_completed(self):
        team, _probe = _planned_team([])

        result = asyncio.run(team.aprocess_request("no planned steps"))

        assert result.status == TaskStatus.FAILED
        assert result.steps_completed == 0
        assert result.steps_total == 0

    def test_missing_agent_is_explicit_failure(self):
        steps = [PlanStep("step-missing", "Missing Agent", "missing", "missing executor")]
        team, _probe = _planned_team(steps)
        team.agents = {}

        result = asyncio.run(team.aprocess_request("missing agent"))

        assert result.status == TaskStatus.FAILED
        assert result.steps_completed == 0
        assert result.steps_total == 1
        assert result.step_results[0].status == TaskStatus.FAILED
        assert "no agent registered" in result.step_results[0].output

    def test_unknown_dependency_blocks_plan(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "depends on missing", depends_on=("missing-step",))
        ]
        team, _probe = _planned_team(steps)

        result = asyncio.run(team.aprocess_request("unknown dependency"))

        assert result.status == TaskStatus.BLOCKED
        assert result.steps_completed == 0
        assert result.step_results[0].status == TaskStatus.BLOCKED
        assert "unknown dependencies" in result.step_results[0].output

    def test_failed_dependency_blocks_descendants(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "failing prerequisite"),
            PlanStep("step-b", "Agent B", "b", "blocked descendant", depends_on=("step-a",)),
        ]
        team, probe = _planned_team(steps)

        class FailedAgent(_ProbeAgent):
            def process(self, request, context=None):
                return TaskResult(
                    task_id="result-a",
                    agent_name=self.name,
                    agent_role=self.role_name,
                    status=TaskStatus.FAILED,
                    output="simulated prerequisite failure",
                )

        team.agents["a"] = FailedAgent("Agent A", "a", probe)

        result = asyncio.run(team.aprocess_request("failure propagation"))

        by_task = {item.task_id: item for item in result.step_results}
        assert result.status == TaskStatus.FAILED
        assert result.steps_completed == 0
        assert by_task["result-a"].status == TaskStatus.FAILED
        assert by_task["step-b"].status == TaskStatus.BLOCKED

    def test_dependency_cycle_blocks_every_unrunnable_step(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "depends on B", depends_on=("step-b",)),
            PlanStep("step-b", "Agent B", "b", "depends on A", depends_on=("step-a",)),
        ]
        team, _probe = _planned_team(steps)

        result = asyncio.run(team.aprocess_request("dependency cycle"))

        assert result.status == TaskStatus.BLOCKED
        assert result.steps_completed == 0
        assert all(item.status == TaskStatus.BLOCKED for item in result.step_results)

    def test_partial_success_count_does_not_hide_failed_team_status(self):
        steps = [
            PlanStep("step-a", "Agent A", "a", "failing task"),
            PlanStep("step-b", "Agent B", "b", "successful independent task"),
        ]
        team, probe = _planned_team(steps)

        class FailedAgent(_ProbeAgent):
            def process(self, request, context=None):
                return TaskResult(
                    task_id="result-a",
                    agent_name=self.name,
                    agent_role=self.role_name,
                    status=TaskStatus.FAILED,
                    output="simulated failure",
                )

        team.agents["a"] = FailedAgent("Agent A", "a", probe)

        result = asyncio.run(team.aprocess_request("partial success"))

        assert result.status == TaskStatus.FAILED
        assert result.steps_completed == 1
        assert result.steps_total == 2

    def test_failed_team_output_does_not_present_successful_synthesis(self):
        steps = [PlanStep("step-a", "Agent A", "a", "failing task")]
        team, probe = _planned_team(steps)

        class FailedAgent(_ProbeAgent):
            def process(self, request, context=None):
                return TaskResult(
                    task_id="result-a",
                    agent_name=self.name,
                    agent_role=self.role_name,
                    status=TaskStatus.FAILED,
                    output="simulated failure detail",
                )

        team.agents["a"] = FailedAgent("Agent A", "a", probe)

        result = asyncio.run(team.aprocess_request("failed synthesis"))

        assert result.status == TaskStatus.FAILED
        assert "Team execution FAILED" in result.final_output
        assert "simulated failure detail" in result.final_output
        assert "synthesized" not in result.final_output
        assert result.confidence == 0.0

    def test_timeout_marks_step_failed_and_team_failed(self):
        steps = [PlanStep("step-a", "Agent A", "a", "slow task")]
        team, _probe = _planned_team(steps, step_timeout=0.01)

        result = asyncio.run(team.aprocess_request("timeout task"))

        assert result.status == TaskStatus.FAILED
        assert result.steps_completed == 0
        assert result.step_results[0].status == TaskStatus.FAILED
        assert "Timeout after 0.01s" in result.step_results[0].output

    def test_process_request_code(self):
        """สั่งงานเขียนโค้ด → Engineer รับงาน."""
        team = TeamDirector()
        result = team.process_request("สร้างระบบเขียนโค้ด API")
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed > 0
        assert "Engineer" in result.team_members_used

    def test_process_request_security(self):
        """สั่งงานความปลอดภัย → Guardian รับงาน."""
        team = TeamDirector()
        result = team.process_request("ตรวจสอบ security credential management")
        assert result.status == TaskStatus.COMPLETED
        assert "Guardian" in result.team_members_used

    def test_process_request_integration(self):
        """สั่งงานเชื่อมต่อ → Connector รับงาน."""
        team = TeamDirector()
        result = team.process_request("เชื่อมต่อ Gmail API integration")
        assert result.status == TaskStatus.COMPLETED
        assert "Connector" in result.team_members_used

    def test_process_request_analysis(self):
        """สั่งงานวิเคราะห์ข้อมูล → Analyst รับงาน."""
        team = TeamDirector()
        result = team.process_request("วิเคราะห์ข้อมูลและสรุปผล")
        assert result.status == TaskStatus.COMPLETED
        assert "Analyst" in result.team_members_used

    def test_process_request_research(self):
        """สั่งงานวิจัย → Researcher รับงาน."""
        team = TeamDirector()
        result = team.process_request("ค้นหาเครื่องมือเปรียบเทียบ AI tools")
        assert result.status == TaskStatus.COMPLETED
        assert "Researcher" in result.team_members_used

    def test_process_request_design(self):
        """สั่งงานออกแบบ → Designer รับงาน."""
        team = TeamDirector()
        result = team.process_request("ออกแบบ UI หน้า dashboard")
        assert result.status == TaskStatus.COMPLETED
        assert "Designer" in result.team_members_used

    def test_multi_agent_collaboration(self):
        """งานที่ต้องทำงานร่วมกันหลาย Agent."""
        team = TeamDirector()
        result = team.process_request("สร้างระบบเชื่อม Gmail อ่านอีเมล วิเคราะห์ข้อมูล ออกแบบ UI")
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed >= 2

    def test_team_status(self):
        """ตรวจสอบสถานะทีม."""
        team = TeamDirector()
        status = team.team_status()
        assert "agents" in status
        assert len(status["agents"]) == 7  # Director + 6 agents
        assert "knowledge_stats" in status

    def test_add_agent(self):
        """เพิ่ม Agent ใหม่."""
        team = TeamDirector()

        class TranslatorAgent(Agent):
            def process(self, request, context=None):
                from creator_app.ai_team.agent_models import TaskResult, generate_id

                return TaskResult(
                    task_id=generate_id("trans"),
                    agent_name=self.name,
                    agent_role=self.role.value,
                    status=TaskStatus.COMPLETED,
                    output="แปลภาษาเสร็จ",
                )

        translator = TranslatorAgent(
            name="Translator",
            role=AgentRole.RESEARCHER,
            expertise=("translation", "thai", "english"),
        )
        team.add_agent("Translator", translator)
        assert "Translator" in team.agents

    def test_remove_agent(self):
        """ลบ Agent."""
        team = TeamDirector()
        assert team.remove_agent("engineer")
        assert "engineer" not in team.agents
        assert not team.remove_agent("NonExistent")

    def test_history(self):
        """ดูประวัติการทำงาน."""
        team = TeamDirector()
        team.process_request("เขียนโค้ด test")
        team.process_request("ตรวจสอบ security")
        history = team.get_history()
        assert len(history) == 2


class TestSharedKnowledge:
    """ทดสอบ Shared Knowledge."""

    def test_add_and_search(self):
        """เพิ่มและค้นหาความรู้."""
        knowledge = SharedKnowledge()
        knowledge.add(
            topic="Gmail OAuth2",
            agent_name="Connector",
            content="วิธีเชื่อมต่อ Gmail ผ่าน OAuth2",
            keywords=("gmail", "oauth2", "email"),
            confidence=0.9,
        )
        results = knowledge.search("เชื่อมต่อ Gmail")
        assert len(results) > 0
        assert "gmail" in results[0].keywords

    def test_search_relevance(self):
        """ค้นหาต้องให้ผลลัพธ์ที่เกี่ยวข้อง."""
        knowledge = SharedKnowledge()
        knowledge.add("Gmail OAuth2", "Connector", "content1", ("gmail",), 0.9)
        knowledge.add("Database SQL", "Engineer", "content2", ("database",), 0.8)
        knowledge.add("Telegram Bot", "Connector", "content3", ("telegram",), 0.7)

        results = knowledge.search("gmail email")
        assert len(results) > 0
        # Gmail entry should be ranked higher
        assert results[0].topic == "Gmail OAuth2"

    def test_stats(self):
        """ตรวจสอบสถิติ."""
        knowledge = SharedKnowledge()
        knowledge.add("topic1", "Engineer", "content1", (), 0.9)
        knowledge.add("topic2", "Guardian", "content2", (), 0.8)
        stats = knowledge.stats()
        assert stats["total_entries"] == 2
        assert stats["by_agent"]["Engineer"] == 1

    def test_persistence(self, tmp_path):
        """บันทึกและโหลดจากไฟล์."""
        path = tmp_path / "knowledge.json"
        k1 = SharedKnowledge(persistence_path=str(path))
        k1.add("topic", "Agent", "content", ("key",), 0.9)

        k2 = SharedKnowledge(persistence_path=str(path))
        assert len(k2.search("topic")) > 0


class TestAgentBase:
    """ทดสอบ Agent base class."""

    def test_confidence_calculation(self):
        """คำนวณความมั่นใจ."""
        from creator_app.ai_team.agents.engineer import EngineerAgent

        agent = EngineerAgent()
        assert agent.confidence_for(("python", "api")) > 0
        assert agent.confidence_for(("nonexistent",)) == 0

    def test_can_handle(self):
        """ตรวจสอบว่าจัดการได้หรือไม่."""
        from creator_app.ai_team.agents.engineer import EngineerAgent

        agent = EngineerAgent()
        assert agent.can_handle(("python",))
        assert agent.can_handle(("javascript",))
        assert not agent.can_handle(("gardening",))

    def test_status(self):
        """สถานะ Agent."""
        from creator_app.ai_team.agents.guardian import GuardianAgent

        agent = GuardianAgent()
        status = agent.status()
        assert status["name"] == "Guardian"
        assert status["role"] == "guardian"
        assert len(status["expertise"]) > 0
