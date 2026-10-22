from __future__ import annotations

import creator_app.agnes.mcp_server as mcp_server


def test_auto_dispatch_development_exposes_control_plane_graph(monkeypatch):
    class FakeSystem:
        def process(self, request: str, *, priority: int = 2) -> str:
            return "PLAN-ONLY"

    monkeypatch.setattr(mcp_server, "get_system", lambda: FakeSystem())
    result = mcp_server.cknexus_auto_dispatch("แก้บั๊ก MCP")

    assert result["execution_state"] == "PLANNED_NOT_EXECUTED"
    assert result["control_plane"]["production_status"] == "NO-GO"
    assert result["control_plane"]["external_mutation_authorized"] is False
    assert len(result["control_plane"]["nodes"]) == 4


def test_auto_dispatch_normal_question_stays_on_reply_path(monkeypatch):
    class FakeReply:
        def reply(self, request: str, *, max_tokens: int = 512):
            return {"response": "ok", "provider": "mock", "model": "mock"}

    monkeypatch.setattr(mcp_server, "AutoReplyPlugin", FakeReply)
    result = mcp_server.cknexus_auto_dispatch("What is MCP?")
    assert result["mode"] == "answer"
    assert "control_plane" not in result


def test_autonomy_status_combines_live_workers_and_redacted_provider_state(monkeypatch):
    class FakeFabric:
        def discover(self):
            return [
                {
                    "assistant_id": "opencode",
                    "available": True,
                    "command": "opencode",
                    "capabilities": ["code_edit"],
                }
            ]

        def select(self, required_capabilities, *, limit=3, require_installed=True):
            if "code_edit" in required_capabilities:
                return [{"assistant_id": "opencode", "available": True}][:limit]
            return []

    class FakeReply:
        def status(self):
            return {
                "configured": True,
                "providers": [{"model": "mock", "healthy": True}],
                "secret_values_exposed": False,
            }

    monkeypatch.setattr(mcp_server, "get_dev_assistant_fabric", lambda: FakeFabric())
    monkeypatch.setattr(mcp_server, "AutoReplyPlugin", FakeReply)
    result = mcp_server.cknexus_autonomy_status()

    assert result["status"] == "inventory_only"
    assert result["secret_values_exposed"] is False
    assert result["assistants"][0]["available"] is True
    assert result["providers"]["providers"][0]["healthy"] is True
    assert {role["role"] for role in result["routing_roles"]} == {
        "research",
        "implementation",
        "verification",
        "security",
    }


def test_task_queue_happy_path_uses_isolated_store(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))

    enqueued = mcp_server.cknexus_task_enqueue(
        "job-1", "verify control plane", priority=2, context="unit-test"
    )
    assert enqueued["ok"] is True
    claimed = mcp_server.cknexus_task_claim("worker-1", lease_seconds=60)
    assert claimed["ok"] is True
    token = claimed["task"]["lease_token"]
    assert token

    checkpoint = mcp_server.cknexus_task_checkpoint(
        "job-1", "worker-1", token, {"stage": "verification"}
    )
    assert checkpoint["ok"] is True

    finished = mcp_server.cknexus_task_finish(
        "job-1", "worker-1", token, True, result={"passed": 1}
    )
    assert finished["ok"] is True
    status = mcp_server.cknexus_task_status("job-1")
    assert status["ok"] is True
    assert status["task"]["state"] == "completed"
    assert "lease_token" not in status["task"]


def test_task_queue_rejects_duplicate_and_empty_queue(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    assert mcp_server.cknexus_task_enqueue("job-1", "one")["ok"] is True
    duplicate = mcp_server.cknexus_task_enqueue("job-1", "two")
    assert duplicate["error_code"] == "DUPLICATE_JOB"
    first = mcp_server.cknexus_task_claim("worker-1")
    assert first["ok"] is True
    second = mcp_server.cknexus_task_claim("worker-1")
    assert second["error_code"] == "EMPTY_QUEUE"


def test_task_queue_stale_lease_is_fenced(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    mcp_server.cknexus_task_enqueue("job-1", "fence")
    first = mcp_server.cknexus_task_claim("worker-1", lease_seconds=0)
    token = first["task"]["lease_token"]
    assert mcp_server.cknexus_task_requeue_expired()["requeued"] == 1
    second = mcp_server.cknexus_task_claim("worker-1", lease_seconds=60)
    assert second["task"]["lease_token"] != token
    stale = mcp_server.cknexus_task_finish("job-1", "worker-1", token, True)
    assert stale["error_code"] == "LEASE_CONFLICT"


def test_task_queue_rejects_oversize_and_secret_shaped_payloads(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    oversized = mcp_server.cknexus_task_enqueue("job-big", "x" * 20_001)
    assert oversized["error_code"] == "PAYLOAD_TOO_LARGE"
    secret = mcp_server.cknexus_task_enqueue(
        "job-secret", "use this", context={"api_key": "not-a-real-key"}
    )
    assert secret["error_code"] == "SENSITIVE_INPUT"


def test_task_queue_does_not_call_external_model(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    monkeypatch.setattr(
        mcp_server,
        "AutoReplyPlugin",
        lambda: (_ for _ in ()).throw(AssertionError("model call")),
    )
    assert mcp_server.cknexus_task_enqueue("job-1", "no model")["ok"] is True


def test_worker_once_executes_only_explicit_safe_canary_job(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    enqueued = mcp_server.cknexus_task_enqueue(
        "job-canary", "safe worker canary", handler="safe_canary"
    )
    assert enqueued["ok"] is True
    result = mcp_server.cknexus_task_worker_once("job-canary")
    assert result["ok"] is True
    assert result["state"] == "completed"
    assert result["release_evidence"] is True
    assert result["production_status"] == "NO-GO"
    assert result["external_mutation_authorized"] is False
    status = mcp_server.cknexus_task_status("job-canary")
    assert status["task"]["state"] == "completed"
    assert "lease_token" not in status["task"]


def test_worker_once_rejects_tasks_without_explicit_handler(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    enqueued = mcp_server.cknexus_task_enqueue("job-plain", "queue only")
    assert enqueued["ok"] is True
    result = mcp_server.cknexus_task_worker_once("job-plain")
    assert result["error_code"] == "WORKER_NOT_OPTED_IN"
    assert mcp_server.cknexus_task_status("job-plain")["task"]["state"] == "queued"


def test_enqueue_rejects_unapproved_worker_handler(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    result = mcp_server.cknexus_task_enqueue(
        "job-unsafe", "must not run", handler="arbitrary_shell"
    )
    assert result["error_code"] == "UNAPPROVED_HANDLER"


def test_control_plane_enqueue_persists_plan_graph_without_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    result = mcp_server.cknexus_control_plane_enqueue(
        "plan-1", "improve MCP routing", priority=2, context="unit-test"
    )
    assert result["ok"] is True
    assert len(result["jobs"]) == 4
    assert result["execution_state"] == "QUEUED_NOT_EXECUTED"
    assert result["production_status"] == "NO-GO"
    assert result["external_mutation_authorized"] is False
    first = mcp_server.cknexus_task_status("plan-1-task-01-research")
    implementation = mcp_server.cknexus_task_status("plan-1-task-02-implementation")
    assert first["task"]["state"] == "queued"
    assert implementation["task"]["state"] == "queued"
    import json

    payload = json.loads(implementation["task"]["payload_json"])
    assert payload["depends_on"] == ["task-01-research"]
    assert payload["external_mutation_authorized"] is False


def test_control_plane_enqueue_rejects_duplicate_prefix_atomically_enough(monkeypatch, tmp_path):
    monkeypatch.setenv("CKNEXUS_TASK_DB", str(tmp_path / "tasks.sqlite3"))
    first = mcp_server.cknexus_control_plane_enqueue("plan-dup", "one")
    assert first["ok"] is True
    second = mcp_server.cknexus_control_plane_enqueue("plan-dup", "two")
    assert second["ok"] is False
    assert second["error_code"] == "DUPLICATE_JOB"
