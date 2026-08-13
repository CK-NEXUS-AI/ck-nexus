from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi.testclient import TestClient

from creator_app.api import create_app
from creator_app.config import Settings
from creator_app.observability import (
    MetricsRegistry,
    RequestObservation,
    StructuredLogger,
    correlation_id,
    redact,
)


def test_correlation_id_preserves_safe_and_replaces_unsafe():
    assert correlation_id("abc-123") == "abc-123"
    assert correlation_id("bad value") != "bad value"
    assert correlation_id("").startswith("ck_")


def test_redaction_is_recursive():
    payload = redact({"token": "secret", "nested": {"api_key": "key", "ok": "value"}})
    assert payload == {"token": "[REDACTED]", "nested": {"api_key": "[REDACTED]", "ok": "value"}}


def test_structured_logger_never_emits_secret(caplog):
    caplog.set_level(logging.INFO, logger="cknexus.observability")
    StructuredLogger().emit(
        "test", token="never-print-this", nested={"password": "never-print-this-either"}
    )
    text = caplog.text
    assert "never-print-this" not in text
    assert "[REDACTED]" in text
    assert json.loads(caplog.records[-1].message)["event"] == "test"


def test_metrics_registry_emits_http_metrics():
    registry = MetricsRegistry()
    registry.observe(RequestObservation("GET", "/health", 200, 0.01))
    registry.observe(RequestObservation("GET", "/health", 503, 0.02))
    text = "\n".join(registry.render_prometheus())
    assert 'ckn_http_requests_total{method="GET",route="/health",status_class="2xx"} 1' in text
    assert 'ckn_http_requests_total{method="GET",route="/health",status_class="5xx"} 1' in text
    assert 'ckn_http_5xx_total{method="GET",route="/health"} 1' in text


def test_creator_api_correlation_header_and_metrics(tmp_path: Path):
    settings = Settings(database_path=tmp_path / "creator.db", mock_ai=True)
    with TestClient(create_app(settings)) as client:
        response = client.get("/health/live", headers={"X-Correlation-ID": "corr-r20"})
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == "corr-r20"
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "ckn_http_requests_total" in metrics.text
        assert "ckn_process_uptime_seconds" in metrics.text


def test_alert_rules_contain_required_signals():
    text = (Path(__file__).resolve().parents[1] / "observability" / "alert_rules.yaml").read_text()
    for rule in ("CKNexusHigh5xxRate", "CKNexusEmailStaleLeases", "CKNexusEmailOutboxBacklog"):
        assert rule in text
