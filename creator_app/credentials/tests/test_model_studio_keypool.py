from __future__ import annotations

import pytest

from creator_app.credentials.free_providers import AUTO_DISCOVER_PROVIDERS
from creator_app.credentials.llm_keypool import KeyPoolError, LlmKeyPool

MODEL_STUDIO_KEYS = [
    *(f"MODEL_STUDIO_API_KEY_{index}" for index in range(1, 10)),
    "MODEL_STUDIO_API_KEY",
    "DASHSCOPE_API_KEY",
]


def clear_provider_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CKNEXUS_LLM_KEYS", raising=False)
    monkeypatch.delenv("MODEL_STUDIO_BASE_URL", raising=False)
    monkeypatch.delenv("MODEL_STUDIO_MODEL", raising=False)
    for env_var in MODEL_STUDIO_KEYS:
        monkeypatch.delenv(env_var, raising=False)
    for provider in AUTO_DISCOVER_PROVIDERS:
        monkeypatch.delenv(provider.env_var, raising=False)


def test_model_studio_keys_use_workspace_endpoint_and_qwen_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_provider_environment(monkeypatch)
    monkeypatch.setenv("MODEL_STUDIO_API_KEY_1", "test-key-one")
    monkeypatch.setenv("MODEL_STUDIO_API_KEY_2", "test-key-two")

    pool = LlmKeyPool.from_environment()

    assert pool is not None
    assert [spec.id for spec in pool.specs] == ["model-studio-1", "model-studio-2"]
    assert {spec.env_var for spec in pool.specs} == {
        "MODEL_STUDIO_API_KEY_1",
        "MODEL_STUDIO_API_KEY_2",
    }
    assert all(
        spec.base_url
        == "https://ws-6qwky1k48cpsbpbq.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
        for spec in pool.specs
    )
    assert all(spec.model == "qwen3.6-plus" and not spec.free for spec in pool.specs)


def test_dashscope_alias_can_override_model_and_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_provider_environment(monkeypatch)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "test-dashscope-key")
    monkeypatch.setenv(
        "MODEL_STUDIO_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setenv("MODEL_STUDIO_MODEL", "qwen-plus")

    pool = LlmKeyPool.from_environment()

    assert pool is not None
    assert len(pool.specs) == 1
    assert pool.specs[0].env_var == "DASHSCOPE_API_KEY"
    assert pool.specs[0].base_url == "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    assert pool.specs[0].model == "qwen-plus"


@pytest.mark.parametrize(
    "base_url",
    [
        "http://ws-6qwky1k48cpsbpbq.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
        "https://attacker.example/compatible-mode/v1",
        "https://ws-6qwky1k48cpsbpbq.ap-southeast-1.maas.aliyuncs.com/v1",
    ],
)
def test_rejects_unsafe_or_wrong_region_model_studio_endpoint(
    monkeypatch: pytest.MonkeyPatch, base_url: str
) -> None:
    clear_provider_environment(monkeypatch)
    monkeypatch.setenv("MODEL_STUDIO_API_KEY_1", "test-secret-not-for-logs")
    monkeypatch.setenv("MODEL_STUDIO_BASE_URL", base_url)

    with pytest.raises(KeyPoolError, match="MODEL_STUDIO_BASE_URL"):
        LlmKeyPool.from_environment()


def test_model_studio_is_blocked_in_unattended_free_only_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured cloud credentials must not trigger potentially billable calls."""
    clear_provider_environment(monkeypatch)
    monkeypatch.setenv("MODEL_STUDIO_API_KEY_1", "test-key-one")
    monkeypatch.setenv("MODEL_STUDIO_API_KEY_2", "test-key-two")

    pool = LlmKeyPool.from_environment()
    assert pool is not None
    assert all(not spec.free for spec in pool.specs)
    assert pool.acquire() is None
    assert pool.free_fallback is True


def test_hosted_provider_registry_does_not_claim_unlimited_free() -> None:
    """No hosted provider is asserted to be unlimited and zero-cost by default."""
    assert AUTO_DISCOVER_PROVIDERS
    assert all(provider.free is False for provider in AUTO_DISCOVER_PROVIDERS)
