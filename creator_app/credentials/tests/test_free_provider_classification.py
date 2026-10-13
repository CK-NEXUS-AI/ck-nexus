from __future__ import annotations

from creator_app.credentials.free_providers import AUTO_DISCOVER_PROVIDERS


def _by_id() -> dict[str, object]:
    return {provider.id: provider for provider in AUTO_DISCOVER_PROVIDERS}


def test_only_exact_zero_cost_route_is_auto_marked_free() -> None:
    providers = _by_id()
    free_ids = {provider.id for provider in AUTO_DISCOVER_PROVIDERS if provider.free}

    assert free_ids == {"openrouter"}
    assert providers["openrouter"].model == "openrouter/free"


def test_commercial_or_tier_dependent_providers_fail_closed() -> None:
    providers = _by_id()

    for provider_id in {
        "openai",
        "deepseek",
        "together",
        "groq",
        "mistral",
        "cerebras",
        "sambanova",
        "zhipu",
        "qwen",
        "gemini",
        "moonshot",
    }:
        assert providers[provider_id].free is False


def test_auto_discovery_ids_are_unique() -> None:
    ids = [provider.id for provider in AUTO_DISCOVER_PROVIDERS]
    assert len(ids) == len(set(ids))
