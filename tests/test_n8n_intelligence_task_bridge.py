from creator_app.n8n_intelligence.models import DevelopmentSignal
from creator_app.n8n_intelligence.task_bridge import build_task


def test_task_payload_is_typed_non_production():
    signal = DevelopmentSignal("e1", "exec-1", "bug", "high", "Fix failure", "boom", 3)
    job_id, payload = build_task(signal, 3)
    assert job_id.startswith("n8n-")
    assert payload["handler"] == "n8n_development_signal"
    assert payload["production_status"] == "NO-GO"
    assert payload["external_mutation_authorized"] is False
    assert "command" not in payload
