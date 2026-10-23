from __future__ import annotations

from creator_app.ai_team.universal_system import (
    CrossPlatform,
    DataHub,
    EnhancedUniversalSystem,
    SecurityLayer,
    SmartAgent,
    UniversalSystem,
)


class TestSmartAgent:
    """ทดสอบ Smart Agent — Auto-Tool Selection."""

    def test_select_gmail_tools(self):
        agent = SmartAgent()
        tools = agent.select_tools("อ่านอีเมลจาก Gmail")
        assert any(t.name == "gmail" for t in tools)

    def test_select_sheets_tools(self):
        agent = SmartAgent()
        tools = agent.select_tools("บันทึกข้อมูลลง Google Sheets")
        assert any(t.name == "google_sheets" for t in tools)

    def test_select_multi_tools(self):
        agent = SmartAgent()
        tools = agent.select_tools("เชื่อม Gmail อ่านอีเมล บันทึก Sheets แจ้ง Slack")
        names = [t.name for t in tools]
        assert "gmail" in names
        assert "google_sheets" in names
        assert "slack" in names

    def test_select_code_tools(self):
        agent = SmartAgent()
        tools = agent.select_tools("เขียนโค้ด Python")
        assert any(t.name == "code" for t in tools)

    def test_select_security_tools(self):
        agent = SmartAgent()
        tools = agent.select_tools("ตรวจสอบ security audit")
        assert any(t.name == "security_scan" for t in tools)

    def test_tool_chain(self):
        agent = SmartAgent()
        tools = agent.select_tools("ดึงอีเมล Gmail บันทึก Sheets แจ้ง Slack")
        chain = agent.chain_tools(tools, "test request")
        assert len(chain) > 0
        assert chain[0]["step"] == 1

    def test_no_match(self):
        agent = SmartAgent()
        tools = agent.select_tools("คำขอที่ไม่ตรงกับเครื่องมือใดเลย")
        assert len(tools) == 0


class TestSecurityLayer:
    """ทดสอบ Security Layer."""

    def test_secret_shield_redacts(self):
        sec = SecurityLayer()
        result = sec.secret_shield("my key is sk-abc123xyz")
        assert "sk-abc123xyz" not in result
        assert "[REDACTED" in result

    def test_secret_shield_no_match(self):
        sec = SecurityLayer()
        result = sec.secret_shield("ข้อความปกติทั่วไป")
        assert result == "ข้อความปกติทั่วไป"

    def test_permission_gate_sensitive(self):
        sec = SecurityLayer()
        result = sec.permission_gate("read", "gmail")
        assert result["requires_permission"] is True

    def test_permission_gate_non_sensitive(self):
        sec = SecurityLayer()
        result = sec.permission_gate("run", "shell")
        assert result["requires_permission"] is False

    def test_scope_limiter(self):
        sec = SecurityLayer()
        result = sec.scope_limiter(
            "gmail.read gmail.send calendar.read", ["gmail.read", "drive.read"]
        )
        assert "gmail.read" in result
        assert "drive.read" not in result

    def test_audit_log(self):
        sec = SecurityLayer()
        sec.audit("test", "agent", "target", "ok")
        log = sec.get_audit_log()
        assert len(log) == 1
        assert log[0]["action"] == "test"


class TestDataHub:
    """ทดสอบ Data Hub."""

    def test_unified_search(self):
        hub = DataHub()
        results = hub.unified_search("อีเมล")
        assert "Gmail" in results

    def test_smart_sync(self):
        hub = DataHub()
        result = hub.smart_sync("Gmail", "Sheets", {"data": "test"})
        assert result["synced"] is True

    def test_build_pipeline(self):
        hub = DataHub()
        pipeline = hub.build_pipeline(
            [
                {"source": "gmail", "action": "read"},
                {"source": "sheets", "action": "write"},
            ]
        )
        assert pipeline["total_steps"] == 2
        assert pipeline["status"] == "ready"


class TestCrossPlatform:
    """ทดสอบ Cross-Platform."""

    def test_detect_platform(self):
        cp = CrossPlatform()
        platform = cp.detect_platform()
        assert platform in ("linux", "macos", "windows")

    def test_get_capabilities(self):
        cp = CrossPlatform()
        caps = cp.get_capabilities("linux")
        assert "shell" in caps
        assert "git" in caps

    def test_cross_platform_task(self):
        cp = CrossPlatform()
        result = cp.cross_platform_task("deploy app")
        assert "current_platform" in result
        assert result["status"] == "ready"


class TestEnhancedUniversalSystemCachePolicy:
    def test_changed_parameters_do_not_use_semantic_cache(self):
        system = EnhancedUniversalSystem(
            enable_cache=True,
            enable_parallel=False,
            enable_auto_route=False,
            enable_self_correction=False,
            enable_perspective=False,
            enable_memory=False,
        )
        calls = []

        def process(request, *, priority=2):
            calls.append(request)
            return f"result for {request}"

        system.base.process = process
        first = system.process("explain 3 categories")
        second = system.process("explain 5 categories")
        assert "Cache Hit" not in first
        assert "Cache Hit" not in second
        assert calls == ["explain 3 categories", "explain 5 categories"]

    def test_exact_static_request_can_still_use_cache(self):
        system = EnhancedUniversalSystem(
            enable_cache=True,
            enable_parallel=False,
            enable_auto_route=False,
            enable_self_correction=False,
            enable_perspective=False,
            enable_memory=False,
        )
        calls = []

        def process(request, *, priority=2):
            calls.append(request)
            return f"static result {len(calls)}"

        system.base.process = process
        system.process("explain a stable concept")
        second = system.process("explain a stable concept")
        assert "Cache Hit" in second
        assert len(calls) == 1

    def test_freshness_sensitive_request_bypasses_cache(self):
        system = EnhancedUniversalSystem(
            enable_cache=True,
            enable_parallel=False,
            enable_auto_route=False,
            enable_self_correction=False,
            enable_perspective=False,
            enable_memory=False,
        )
        calls = []

        def process(request, *, priority=2):
            calls.append(request)
            return f"live result {len(calls)}"

        system.base.process = process
        first = system.process("summarize latest email")
        second = system.process("summarize latest email")
        assert "Cache Hit" not in first
        assert "Cache Hit" not in second
        assert len(calls) == 2


class TestUniversalSystem:
    """ทดสอบ Universal System — รวมทุกระบบ."""

    def test_process_simple(self):
        system = UniversalSystem()
        result = system.process("เขียนโค้ด Python")
        assert "ผลลัพธ์ Universal System" in result
        assert "code" in result.lower() or "Engineer" in result

    def test_process_gmail(self):
        system = UniversalSystem()
        result = system.process("เชื่อม Gmail อ่านอีเมล")
        assert "gmail" in result.lower()

    def test_process_multi(self):
        system = UniversalSystem()
        result = system.process("สร้างระบบเชื่อม Gmail บันทึก Sheets แจ้ง Slack")
        assert "gmail" in result.lower() or "sheets" in result.lower()

    def test_status(self):
        system = UniversalSystem()
        status = system.status()
        assert "team" in status
        assert "tools_registered" in status
        assert status["tools_registered"] > 0

    def test_list_capabilities(self):
        system = UniversalSystem()
        caps = system.list_capabilities()
        assert caps["team_members"] == 7
        assert caps["tools"] > 0
        assert caps["data_sources"] > 0

    def test_secret_shield_in_process(self):
        system = UniversalSystem()
        result = system.process("ส่ง sk-test123abc ไป Slack")
        assert "sk-test123abc" not in result
        assert "[REDACTED" in result

    def test_audit_log_populated(self):
        system = UniversalSystem()
        system.process("ทดสอบ audit")
        assert len(system.security.audit_log) > 0
