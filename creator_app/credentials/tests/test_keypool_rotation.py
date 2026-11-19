"""Tests for LLM key pool auto-rotation at 95% quota threshold."""

from __future__ import annotations

import os

from creator_app.credentials.llm_keypool import (
    LlmKeyPool,
    LlmKeySpec,
)


def test_keypool_rotates_at_95_percent_quota() -> None:
    """When a key reaches 95% usage, it should be marked exhausted."""
    specs = [
        LlmKeySpec(
            id="key1",
            env_var="TEST_KEY1",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
        LlmKeySpec(
            id="key2",
            env_var="TEST_KEY2",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
    ]
    os.environ["TEST_KEY1"] = "sk-test-key1"
    os.environ["TEST_KEY2"] = "sk-test-key2"

    pool = LlmKeyPool(specs)

    # Report quota usage at 96% for key1
    pool.report_quota_usage(key_id="key1", used=96, total=100)

    statuses = pool.status()
    key1_status = next(s for s in statuses if s.key_id == "key1")
    assert key1_status.exhausted is True
    assert key1_status.quota_percentage_used == 96.0

    # key1 should not be acquired, key2 should be
    selection = pool.acquire()
    assert selection is not None
    assert selection.key_id == "key2"

    del os.environ["TEST_KEY1"]
    del os.environ["TEST_KEY2"]


def test_keypool_auto_rotation_preserves_other_keys() -> None:
    """When one key is exhausted, the pool should fall back to the next."""
    specs = [
        LlmKeySpec(
            id="primary",
            env_var="TEST_PRIMARY",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
        LlmKeySpec(
            id="secondary",
            env_var="TEST_SECONDARY",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
        LlmKeySpec(
            id="fallback",
            env_var="TEST_FALLBACK",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
    ]
    os.environ["TEST_PRIMARY"] = "sk-primary"
    os.environ["TEST_SECONDARY"] = "sk-secondary"
    os.environ["TEST_FALLBACK"] = "sk-fallback"

    pool = LlmKeyPool(specs)

    # Exhaust primary
    pool.report_quota_usage(key_id="primary", used=100, total=100)

    # Should acquire secondary
    selection = pool.acquire()
    assert selection.key_id == "secondary"

    # Exhaust secondary too
    pool.report_quota_usage(key_id="secondary", used=100, total=100)

    # Should acquire fallback
    selection = pool.acquire()
    assert selection.key_id == "fallback"

    # Exhaust all
    pool.report_quota_usage(key_id="fallback", used=100, total=100)

    # Should trigger free fallback
    selection = pool.acquire()
    assert selection is None
    assert pool.free_fallback is True

    for key in ("TEST_PRIMARY", "TEST_SECONDARY", "TEST_FALLBACK"):
        del os.environ[key]


def test_keypool_cooldown_on_rate_limit() -> None:
    """429 rate limit should trigger cooldown, not exhaustion."""
    specs = [
        LlmKeySpec(
            id="key1",
            env_var="TEST_RL_KEY",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
    ]
    os.environ["TEST_RL_KEY"] = "sk-test"

    pool = LlmKeyPool(specs, cooldown_429=0.1)
    pool.report_failure("key1", status_code=429)

    statuses = pool.status()
    key1 = next(s for s in statuses if s.key_id == "key1")
    assert key1.healthy is False
    assert not key1.exhausted  # 429 should not mark as exhausted, just cooldown

    del os.environ["TEST_RL_KEY"]


def test_keypool_exhaustion_on_auth_failure() -> None:
    """401/402/403 should mark key as exhausted, not just cooldown."""
    specs = [
        LlmKeySpec(
            id="key1",
            env_var="TEST_E_KEY",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
    ]
    os.environ["TEST_E_KEY"] = "sk-test"

    pool = LlmKeyPool(specs, exhaustion_recheck=3600)
    pool.report_failure("key1", status_code=401)

    statuses = pool.status()
    key1 = next(s for s in statuses if s.key_id == "key1")
    assert key1.exhausted is True
    assert key1.healthy is False

    del os.environ["TEST_E_KEY"]


def test_keypool_free_fallback_when_all_unavailable() -> None:
    """When all keys are exhausted, free_fallback should be True."""
    specs = [
        LlmKeySpec(
            id="k1",
            env_var="TEST_F1",
            base_url="http://127.0.0.1:11434/v1",
            model="local-test-model",
            free=True,
        ),
    ]
    os.environ["TEST_F1"] = "sk-test"

    pool = LlmKeyPool(specs)
    pool.report_quota_usage(key_id="k1", used=100, total=100)

    selection = pool.acquire()
    assert selection is None
    assert pool.free_fallback is True

    del os.environ["TEST_F1"]


def test_unattended_pool_rejects_cloud_route_even_if_marked_free(monkeypatch) -> None:
    """A free-tier label must not authorize an unbounded hosted API route."""
    monkeypatch.setenv("TEST_CLOUD_KEY", "test-cloud-key")
    pool = LlmKeyPool([
        LlmKeySpec(
            id="cloud-free-label",
            env_var="TEST_CLOUD_KEY",
            base_url="https://api.example.com/v1",
            model="some-free-model",
            free=True,
        )
    ])

    assert pool.acquire() is None
    assert pool.free_fallback is True


def test_unattended_pool_allows_local_model_endpoint(monkeypatch) -> None:
    """A configured loopback inference endpoint has no hosted API billing path."""
    monkeypatch.setenv("TEST_LOCAL_KEY", "local-placeholder")
    pool = LlmKeyPool([
        LlmKeySpec(
            id="local-model",
            env_var="TEST_LOCAL_KEY",
            base_url="http://127.0.0.1:11434/v1",
            model="local-model",
            free=True,
        )
    ])

    selection = pool.acquire()
    assert selection is not None
    assert selection.provider == "local-model"
