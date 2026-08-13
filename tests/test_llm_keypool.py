from __future__ import annotations

import json
import os

import pytest

from creator_app.llm_keypool import (
    HttpKeyProber,
    KeyPoolError,
    LlmKeyPool,
    LlmKeySpec,
    ProbeResult,
)


def spec(key_id: str, env: str | None = None) -> LlmKeySpec:
    return LlmKeySpec(
        id=key_id,
        env_var=env or f"K_{key_id}",
        base_url=f"https://{key_id}.example/v1",
        model="m",
    )


class FakeProber:
    def __init__(self, table: dict[str, int | None]) -> None:
        self.table = table
        self.calls: list[str] = []

    def probe(self, spec, api_key, *, timeout):
        self.calls.append(spec.id)
        code = self.table.get(spec.id)
        return ProbeResult(status=code, ok=code == 200, detail=f"http_{code}")


def make_pool(prober: FakeProber, specs: list[LlmKeySpec] | None = None) -> LlmKeyPool:
    specs = specs or [spec("a"), spec("b"), spec("c")]
    for item in specs:
        os.environ[item.env_var] = f"secret-{item.id}"
    return LlmKeyPool(specs, prober=prober, state_path=None)


def test_acquire_returns_first_healthy_key(monkeypatch):
    pool = make_pool(FakeProber({}))
    selection = pool.acquire()
    assert selection is not None
    assert selection.api_key == "secret-a"
    assert selection.key_id == "a"
    assert selection.base_url == "https://a.example/v1"


def test_rotation_advances_round_robin(monkeypatch):
    pool = make_pool(FakeProber({}))
    ids = [pool.acquire().key_id for _ in range(6)]
    assert ids == ["a", "b", "c", "a", "b", "c"]


def test_429_puts_key_in_cooldown_and_rotates(monkeypatch):
    pool = make_pool(FakeProber({}))
    first = pool.acquire()
    pool.report_status(first.key_id, 429)
    second = pool.acquire()
    assert second.key_id != first.key_id
    status = {item.key_id: item for item in pool.status()}
    assert status[first.key_id].healthy is False
    assert status[first.key_id].cooldown_until > 0


def test_cooldown_expires_and_key_returns(monkeypatch):
    os.environ["K_A"] = "secret-a"
    os.environ["K_B"] = "secret-b"
    now = [0.0]

    def clock() -> float:
        return now[0]

    pool = LlmKeyPool(
        [spec("a"), spec("b")],
        prober=FakeProber({}),
        clock=clock,
    )
    first = pool.acquire()
    pool.report_status(first.key_id, 429)
    assert pool.acquire().key_id != first.key_id
    now[0] = 100.0  # cooldown (30s) has expired
    status = {item.key_id: item for item in pool.status()}
    assert status[first.key_id].healthy is True
    assert status[first.key_id].cooldown_until <= 100.0


def test_401_marks_key_exhausted(monkeypatch):
    pool = make_pool(FakeProber({}))
    first = pool.acquire()
    pool.report_status(first.key_id, 401)
    assert pool.acquire().key_id != first.key_id
    status = {item.key_id: item for item in pool.status()}
    assert status[first.key_id].exhausted is True
    assert status[first.key_id].healthy is False


def test_all_keys_unavailable_triggers_free_fallback(monkeypatch):
    pool = make_pool(FakeProber({}))
    for item in pool.status():
        pool.report_status(item.key_id, 401)
    assert pool.acquire() is None
    assert pool.free_fallback is True


def test_probe_all_classifies_keys(monkeypatch):
    pool = make_pool(
        FakeProber({"a": 200, "b": 401, "c": None}),
        specs=[spec("a"), spec("b"), spec("c")],
    )
    pool.probe_all()
    status = {item.key_id: item for item in pool.status()}
    assert status["a"].healthy is True
    assert status["b"].exhausted is True
    assert status["c"].healthy is False  # degraded (network error -> cooldown)


def test_state_persistence_survives_restart(monkeypatch, tmp_path):
    state = str(tmp_path / "pool.json")
    pool = LlmKeyPool(
        [spec("a"), spec("b")],
        prober=FakeProber({}),
        state_path=state,
    )
    first = pool.acquire()
    pool.report_status(first.key_id, 429)
    pool.save_state()

    restored = LlmKeyPool(
        [spec("a"), spec("b")],
        prober=FakeProber({}),
        state_path=state,
    )
    status = {item.key_id: item for item in restored.status()}
    assert status[first.key_id].healthy is False
    assert status[first.key_id].cooldown_until > 0


def test_status_never_leaks_secrets(monkeypatch):
    pool = make_pool(FakeProber({}))
    for item in pool.status():
        assert "secret-" not in str(item)
        import dataclasses

        assert "secret-" not in json.dumps(dataclasses.asdict(item), default=str)


def test_missing_env_key_is_not_selected(monkeypatch):
    specs = [spec("a"), spec("b", env="OTHER_KEY")]
    os.environ["K_A"] = "secret-a"
    monkeypatch.delenv("OTHER_KEY", raising=False)
    pool = LlmKeyPool(specs, prober=FakeProber({}))
    selection = pool.acquire()
    assert selection is not None and selection.key_id == "a"


def test_duplicate_ids_rejected():
    with pytest.raises(KeyPoolError):
        LlmKeyPool([spec("a"), spec("a")], prober=FakeProber({}))


def test_from_environment_parses_cnknxus_llm_keys(monkeypatch):
    monkeypatch.delenv("CKNEXUS_LLM_KEYS", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv(
        "CKNEXUS_LLM_KEYS",
        json.dumps(
            [
                {
                    "id": "k1",
                    "env_var": "K1_KEY",
                    "base_url": "https://k1.example/v1",
                    "model": "m1",
                    "free": True,
                }
            ]
        ),
    )
    monkeypatch.setenv("K1_KEY", "secret-k1")
    pool = LlmKeyPool.from_environment()
    assert pool is not None
    assert pool.acquire().key_id == "k1"


def test_from_environment_returns_none_without_keys(monkeypatch):
    monkeypatch.delenv("CKNEXUS_LLM_KEYS", raising=False)
    for name in ("OPENAI_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY", "MOONSHOT_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    assert LlmKeyPool.from_environment() is None


def test_http_prober_maps_http_errors(monkeypatch):
    import urllib.error

    class _Resp:
        status = 200

    def fake_open(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 401, "unauth", {}, None)

    prober = HttpKeyProber(open_url=fake_open)
    result = prober.probe(spec("a"), "k", timeout=1)
    assert result.status == 401
    assert result.ok is False


def test_quota_429_classified_as_exhaustion():
    assert LlmKeyPool.classify_failure_status(429, "insufficient balance, please recharge") == 402
    assert LlmKeyPool.classify_failure_status(429, "rate limit exceeded") == 429
    assert LlmKeyPool.classify_failure_status(429, "suspended due to quota") == 402
    assert LlmKeyPool.classify_failure_status(401, "bad key") == 401


def test_quota_exhaustion_marks_key_and_rotates(monkeypatch):
    pool = make_pool(FakeProber({}))
    first = pool.acquire()
    pool.report_status(first.key_id, 402)
    assert pool.acquire().key_id != first.key_id
    status = {item.key_id: item for item in pool.status()}
    assert status[first.key_id].exhausted is True
