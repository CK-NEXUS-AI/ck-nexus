from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from creator_app.q11_capability import Q11Status, aggregate_q11, make_gate

SCRIPT = Path(__file__).parents[1] / "scripts" / "test_openai_live.py"


def load_smoke_module():
    spec = importlib.util.spec_from_file_location("q11_openai_live", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeStatusError(Exception):
    def __init__(self, status_code: int, code: str | None = None, request_id: str = "req-test"):
        self.status_code = status_code
        self.body = {"code": code} if code else {}
        self.request_id = request_id


class FakeResponse:
    id = "resp-test"
    output_text = "CK-NEXUS-P0-SMOKE-PASS ทดสอบผ่าน"


def run_main(monkeypatch, tmp_path, exception=None, response=None):
    module = load_smoke_module()
    monkeypatch.setenv("OPENAI_API_KEY", "redacted-test-only")
    monkeypatch.setenv("Q11_EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setenv("Q11_SOURCE_IDENTITY", "git:test")
    fake_openai = types.ModuleType("openai")

    class FakeClient:
        class responses:
            @staticmethod
            def create(**_kwargs):
                if exception is not None:
                    raise exception
                return response or FakeResponse()

    fake_openai.OpenAI = FakeClient
    fake_openai.APIConnectionError = type("APIConnectionError", (Exception,), {})
    fake_openai.APITimeoutError = type("APITimeoutError", (fake_openai.APIConnectionError,), {})
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    return module.main()


def evidence(tmp_path):
    files = list(tmp_path.glob("q11-p02-error-classification-*.json"))
    assert len(files) == 1
    return files[0]


def test_429_insufficient_quota_returns_10_and_blocked_evidence(monkeypatch, tmp_path):
    module = load_smoke_module()
    assert module.classify_exception(FakeStatusError(429, "insufficient_quota"))[0] == 10
    code = run_main(
        monkeypatch,
        tmp_path,
        exception=FakeStatusError(429, "insufficient_quota"),
    )
    assert code == 10
    data = evidence(tmp_path).read_text()
    assert '"classification": "BLOCKED_PROVIDER_QUOTA"' in data
    assert '"http_status": 429' in data
    assert '"provider_code": "insufficient_quota"' in data
    assert '"secret_exposed": false' in data
    assert '"promotion_blocked": true' in data
    assert "redacted-test-only" not in data


def test_401_returns_11(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, exception=FakeStatusError(401, "invalid_api_key"))
    assert code == 11
    assert '"classification": "BLOCKED_PROVIDER_AUTH"' in evidence(tmp_path).read_text()


def test_timeout_returns_12(monkeypatch, tmp_path):
    module = load_smoke_module()
    timeout = type("FakeTimeout", (Exception,), {})
    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = object
    fake_openai.APIConnectionError = timeout
    fake_openai.APITimeoutError = timeout
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    assert module.classify_exception(timeout())[0] == 12


def test_unhandled_returns_99(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, exception=RuntimeError("internal test failure"))
    assert code == 99
    assert '"classification": "UNKNOWN"' in evidence(tmp_path).read_text()


def test_success_returns_0_and_verified_evidence(monkeypatch, tmp_path):
    code = run_main(monkeypatch, tmp_path, response=FakeResponse())
    assert code == 0
    data = evidence(tmp_path).read_text()
    assert '"classification": "VERIFIED"' in data
    assert '"promotion_blocked": false' in data


def test_429_cannot_promote_q11_aggregate():
    meta = dict(
        execution_id="exec-test",
        release_id="release-test",
        commit="a" * 40,
        source_identity="git:test",
        evidence_artifact="evidence/q11-test.json",
        evidence_sha256="sha256:" + "b" * 64,
        verification_method="independent_runtime_execution",
    )

    def gate(gate_id, status, provider=None, block_reason=None):
        return make_gate(
            gate_id,
            status,
            provider=provider,
            block_reason=block_reason,
            **meta,
        )

    gates = {
        "Q11-A": gate("Q11-A", Q11Status.VERIFIED),
        "Q11-B": gate("Q11-B", Q11Status.VERIFIED),
        "Q11-C": gate("Q11-C", Q11Status.VERIFIED, "openai"),
        "Q11-D": gate("Q11-D", Q11Status.VERIFIED, "openai"),
        "Q11-E": gate(
            "Q11-E",
            Q11Status.BLOCKED,
            "openai",
            "openai: insufficient_quota",
        ),
        "Q11-F": gate(
            "Q11-F",
            Q11Status.BLOCKED,
            "openai",
            "openai: insufficient_quota",
        ),
        "Q11-G": gate("Q11-G", Q11Status.VERIFIED),
    }
    assert aggregate_q11(gates) is Q11Status.BLOCKED
