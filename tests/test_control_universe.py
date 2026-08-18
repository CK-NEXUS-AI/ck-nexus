from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.control_universe import install_control_universe


def build_client(tmp_path):
    settings = Settings(
        database_path=tmp_path / "creator.db",
        agnes_ledger_path=tmp_path / "agnes-ledger.jsonl",
        mock_ai=True,
        access_token="test-token",
    )
    app = create_app(settings)
    install_control_universe(app)
    return TestClient(app)


def auth_headers():
    return {"Authorization": "Bearer test-token"}


def test_control_universe_requires_access_for_runtime_data(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get("/api/control-universe/overview")
        assert response.status_code == 401


def test_control_universe_overview_never_claims_production_ready(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get("/api/control-universe/overview", headers=auth_headers())
        assert response.status_code == 200
        payload = response.json()
        assert payload["production"]["status"] == "NO-GO"
        assert payload["evidence"]["kind"] == "HASH_CHAINED_APPEND_ONLY_LEDGER"
        assert payload["evidence"]["immutability_claim"] == "NOT_CLAIMED"
        assert payload["capabilities"]["pause_task"] is False
        assert payload["capabilities"]["resume_task"] is False


def test_control_universe_projects_real_ledger_records(tmp_path):
    with build_client(tmp_path) as client:
        app = client.app
        record = app.state.agnes.ledger.append(
            "tool_execution_verified",
            {
                "task_id": "TASK-1",
                "execution_id": "RUN-1",
                "policy": "R0_READ",
                "decision": "ALLOW",
            },
        )

        response = client.get(
            "/api/control-universe/events?after_seq=0",
            headers=auth_headers(),
        )
        assert response.status_code == 200
        event = response.json()["events"][0]
        assert event["seq"] == record["sequence"]
        assert event["event_type"] == "tool_execution_verified"
        assert event["task_id"] == "TASK-1"
        assert event["run_id"] == "RUN-1"
        assert event["governance"]["decision"] == "ALLOW"
        assert event["evidence_ref"] == record["hash"]


def test_control_universe_mutations_fail_closed_without_adapter(tmp_path):
    with build_client(tmp_path) as client:
        response = client.post(
            "/api/control-universe/tasks/TASK-1/commands/pause",
            headers=auth_headers(),
        )
        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "CONTROL_ADAPTER_UNAVAILABLE"


def test_control_universe_graph_is_labeled_non_authoritative(tmp_path):
    with build_client(tmp_path) as client:
        response = client.get("/api/control-universe/graph", headers=auth_headers())
        assert response.status_code == 200
        payload = response.json()
        assert payload["graph_kind"] == "RUNTIME_CAPABILITY_PROJECTION"
        assert payload["authoritative_task_graph"] is False
        assert payload["nodes"][-1]["id"] == "evidence"
