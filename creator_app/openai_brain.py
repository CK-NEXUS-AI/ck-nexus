from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class OpenAIBrainUnavailable(RuntimeError):
    """Raised when the OpenAI Agents SDK runtime is unavailable."""


@dataclass(frozen=True, slots=True)
class OpenAIBrainRunConfig:
    """Per-run OpenAI runtime objects.

    The provider is intentionally scoped to one run so provider credentials are never
    installed as process-global defaults. This keeps the Credential Broker as the sole
    authority for obtaining the secret and avoids cross-tenant credential bleed.
    """

    provider: Any = field(repr=False)
    run_config: Any = field(repr=False)


def build_openai_agents_run_config(
    *,
    api_key: str,
    model: str,
    workflow_name: str,
    tracing_enabled: bool = False,
    group_id: str | None = None,
    base_url: str | None = None,
) -> OpenAIBrainRunConfig:
    if not api_key:
        raise ValueError("api_key is required")
    if not model.strip():
        raise ValueError("model is required")
    if not workflow_name.strip():
        raise ValueError("workflow_name is required")

    try:
        from agents import OpenAIProvider, RunConfig
    except ImportError as exc:  # pragma: no cover - exercised by runtime integration
        raise OpenAIBrainUnavailable("OpenAI Agents SDK is not installed.") from exc

    provider_kwargs: dict[str, Any] = {"api_key": api_key, "use_responses": True}
    if base_url:
        provider_kwargs["base_url"] = base_url
    provider = OpenAIProvider(**provider_kwargs)
    kwargs: dict[str, Any] = {
        "model": model.strip(),
        "model_provider": provider,
        "workflow_name": workflow_name.strip(),
        "trace_include_sensitive_data": False,
        "tracing_disabled": not tracing_enabled,
    }
    if tracing_enabled:
        # Per-run tracing credential; never mutate the process-global exporter/default key.
        kwargs["tracing"] = {"api_key": api_key}
    if group_id:
        kwargs["group_id"] = group_id

    return OpenAIBrainRunConfig(provider=provider, run_config=RunConfig(**kwargs))
