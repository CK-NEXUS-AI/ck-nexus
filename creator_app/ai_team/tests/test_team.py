from __future__ import annotations

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    AgentRole,
    TaskStatus,
)
from creator_app.ai_team.shared_knowledge import SharedKnowledge
from creator_app.ai_team.team_director import TeamDirector


class TestTeamDirector:
    """ทดสอบ TeamDirector — หัวหน้าทีม."""

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
