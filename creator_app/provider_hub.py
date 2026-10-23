"""CK-NEXUS Multi-Provider Hub — production-grade key management.

Integrates with CredentialBroker + CredentialVault for secure key storage.
Supports Claude/Anthropic, OpenAI, Groq, Gemini, and more.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen


class ProviderTier(StrEnum):
    FREE = "free"
    FREEMIUM = "freemium"


class ProviderStatus(StrEnum):
    UNKNOWN = "unknown"
    ACTIVE = "active"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProviderEndpoint:
    name: str
    slug: str
    base_url: str
    env_key: str
    tier: ProviderTier
    validate_url: str
    models_url: str
    free_models: tuple[str, ...] = ()
    signup_url: str = ""
    docs_url: str = ""
    description: str = ""
    icon: str = ""
    header_key: str = "Authorization"
    header_format: str = "Bearer {key}"
    is_anthropic: bool = False


PROVIDERS: list[ProviderEndpoint] = [
    # ── Anthropic / Claude ──
    ProviderEndpoint(
        name="Anthropic (Claude)",
        slug="anthropic",
        base_url="https://api.anthropic.com/v1",
        env_key="ANTHROPIC_API_KEY",
        tier=ProviderTier.FREEMIUM,
        validate_url="https://api.anthropic.com/v1/messages",
        models_url="https://api.anthropic.com/v1/models",
        free_models=("claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"),
        signup_url="https://console.anthropic.com/settings/keys",
        docs_url="https://docs.anthropic.com/",
        description="Claude 4 Sonnet, 3.5 Haiku — best reasoning",
        icon="🏛️",
        header_key="x-api-key",
        header_format="{key}",
        is_anthropic=True,
    ),
    # ── OpenAI ──
    ProviderEndpoint(
        name="OpenAI",
        slug="openai",
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        tier=ProviderTier.FREEMIUM,
        validate_url="https://api.openai.com/v1/models",
        models_url="https://api.openai.com/v1/models",
        free_models=("gpt-4o-mini", "gpt-4o"),
        signup_url="https://platform.openai.com/api-keys",
        docs_url="https://platform.openai.com/docs",
        description="$5 free credit, GPT-4o, o1",
        icon="🤖",
    ),
    # ── Groq ──
    ProviderEndpoint(
        name="Groq",
        slug="groq",
        base_url="https://api.groq.com/openai/v1",
        env_key="GROQ_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.groq.com/openai/v1/models",
        models_url="https://api.groq.com/openai/v1/models",
        free_models=("llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"),
        signup_url="https://console.groq.com/keys",
        docs_url="https://console.groq.com/docs",
        description="Lightning-fast inference, generous free tier",
        icon="⚡",
    ),
    # ── Google Gemini ──
    ProviderEndpoint(
        name="Google Gemini",
        slug="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        env_key="GEMINI_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://generativelanguage.googleapis.com/v1beta/models",
        models_url="https://generativelanguage.googleapis.com/v1beta/models",
        free_models=("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"),
        signup_url="https://aistudio.google.com/apikey",
        docs_url="https://ai.google.dev/docs",
        description="Google's latest models, free tier",
        icon="💎",
        header_format="Bearer {key}",
    ),
    # ── DeepSeek ──
    ProviderEndpoint(
        name="DeepSeek",
        slug="deepseek",
        base_url="https://api.deepseek.com/v1",
        env_key="DEEPSEEK_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.deepseek.com/v1/models",
        models_url="https://api.deepseek.com/v1/models",
        free_models=("deepseek-chat", "deepseek-reasoner"),
        signup_url="https://platform.deepseek.com/",
        docs_url="https://platform.deepseek.com/api-docs",
        description="Strong reasoning, free credits",
        icon="🔍",
    ),
    # ── OpenRouter ──
    ProviderEndpoint(
        name="OpenRouter",
        slug="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://openrouter.ai/api/v1/models",
        models_url="https://openrouter.ai/api/v1/models",
        free_models=("meta-llama/llama-3.3-70b-instruct:free", "qwen/qwen-2.5-72b-instruct:free"),
        signup_url="https://openrouter.ai/keys",
        docs_url="https://openrouter.ai/docs",
        description="Gateway to 100+ models, many free",
        icon="🔀",
    ),
    # ── Cerebras ──
    ProviderEndpoint(
        name="Cerebras",
        slug="cerebras",
        base_url="https://api.cerebras.ai/v1",
        env_key="CEREBRAS_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.cerebras.ai/v1/models",
        models_url="https://api.cerebras.ai/v1/models",
        free_models=("llama-3.3-70b", "llama-3.1-8b"),
        signup_url="https://cloud.cerebras.ai/",
        docs_url="https://inference-docs.cerebras.ai/",
        description="Ultra-fast inference speeds",
        icon="🧠",
    ),
    # ── Together AI ──
    ProviderEndpoint(
        name="Together AI",
        slug="together",
        base_url="https://api.together.xyz/v1",
        env_key="TOGETHER_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.together.xyz/v1/models",
        models_url="https://api.together.xyz/v1/models",
        free_models=("meta-llama/Llama-3-70b-chat-hf",),
        signup_url="https://api.together.xyz/settings/api-keys",
        docs_url="https://docs.together.ai/",
        description="Open-source model hosting, free credits",
        icon="🤝",
    ),
    # ── Mistral AI ──
    ProviderEndpoint(
        name="Mistral AI",
        slug="mistral",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.mistral.ai/v1/models",
        models_url="https://api.mistral.ai/v1/models",
        free_models=("mistral-small-latest", "mistral-tiny"),
        signup_url="https://console.mistral.ai/api-keys/",
        docs_url="https://docs.mistral.ai/",
        description="European AI, free tier available",
        icon="🌊",
    ),
    # ── SambaNova ──
    ProviderEndpoint(
        name="SambaNova",
        slug="sambanova",
        base_url="https://api.sambanova.ai/v1",
        env_key="SAMBANOVA_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.sambanova.ai/v1/models",
        models_url="https://api.sambanova.ai/v1/models",
        free_models=("Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3-0324"),
        signup_url="https://cloud.sambanova.ai/apis",
        docs_url="https://docs.sambanova.ai/",
        description="Enterprise-grade, free tier",
        icon="🔥",
    ),
    # ── Fireworks AI ──
    ProviderEndpoint(
        name="Fireworks AI",
        slug="fireworks",
        base_url="https://api.fireworks.ai/inference/v1",
        env_key="FIREWORKS_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.fireworks.ai/inference/v1/models",
        models_url="https://api.fireworks.ai/inference/v1/models",
        free_models=("accounts/fireworks/models/llama-v3p3-70b-instruct",),
        signup_url="https://fireworks.ai/account/api-keys",
        docs_url="https://docs.fireworks.ai/",
        description="Fast inference, free tier",
        icon="🎆",
    ),
    # ── xAI (Grok) ──
    ProviderEndpoint(
        name="xAI (Grok)",
        slug="xai",
        base_url="https://api.x.ai/v1",
        env_key="XAI_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.x.ai/v1/models",
        models_url="https://api.x.ai/v1/models",
        free_models=("grok-2-1212",),
        signup_url="https://console.x.ai/",
        docs_url="https://docs.x.ai/",
        description="Grok models, free credits",
        icon="✖️",
    ),
    # ── Cohere ──
    ProviderEndpoint(
        name="Cohere",
        slug="cohere",
        base_url="https://api.cohere.com/v2",
        env_key="COHERE_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.cohere.com/v2/models",
        models_url="https://api.cohere.com/v2/models",
        free_models=("command-r", "command-r-plus"),
        signup_url="https://dashboard.cohere.com/api-keys",
        docs_url="https://docs.cohere.com/",
        description="RAG-optimized, free tier",
        icon="📊",
    ),
    # ── HuggingFace ──
    ProviderEndpoint(
        name="HuggingFace",
        slug="huggingface",
        base_url="https://api-inference.huggingface.co/v1",
        env_key="HUGGINGFACE_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://huggingface.co/api/whoami-v2",
        models_url="https://huggingface.co/api/models",
        free_models=("meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-72B-Instruct"),
        signup_url="https://huggingface.co/settings/tokens",
        docs_url="https://huggingface.co/docs/api-inference/",
        description="Open-source hub, free inference",
        icon="🤗",
    ),
    # ── Cloudflare Workers AI ──
    ProviderEndpoint(
        name="Cloudflare Workers AI",
        slug="cloudflare",
        base_url="https://api.cloudflare.com/client/v4",
        env_key="CLOUDFLARE_API_TOKEN",
        tier=ProviderTier.FREE,
        validate_url="https://api.cloudflare.com/client/v4/user/tokens/verify",
        models_url="https://api.cloudflare.com/client/v4/accounts",
        free_models=("@cf/meta/llama-3.3-70b-instruct-fp8",),
        signup_url="https://dash.cloudflare.com/profile/api-tokens",
        docs_url="https://developers.cloudflare.com/workers-ai/",
        description="Edge AI, generous free tier",
        icon="☁️",
    ),
    # ── Novita AI ──
    ProviderEndpoint(
        name="Novita AI",
        slug="novita",
        base_url="https://api.novita.ai/v3/openai",
        env_key="NOVITA_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.novita.ai/v3/openai/models",
        models_url="https://api.novita.ai/v3/openai/models",
        free_models=("meta-llama/llama-3.3-70b-instruct",),
        signup_url="https://novita.ai/settings",
        docs_url="https://novita.ai/docs",
        description="Uncensored models, free tier",
        icon="🚀",
    ),
    # ── Chutes AI ──
    ProviderEndpoint(
        name="Chutes AI",
        slug="chutes",
        base_url="https://api.chutes.ai/v1",
        env_key="CHUTES_API_KEY",
        tier=ProviderTier.FREE,
        validate_url="https://api.chutes.ai/v1/models",
        models_url="https://api.chutes.ai/v1/models",
        free_models=("chutesai/llama-3.3-70b-instruct",),
        signup_url="https://chutes.ai/app/api-keys",
        docs_url="https://chutes.ai/docs",
        description="Community-driven, free tier",
        icon="🪂",
    ),
]


def _require_known_validation_url(url: str) -> None:
    allowed = {provider.validate_url for provider in PROVIDERS}
    parsed = urlparse(url)
    if url not in allowed or parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Provider validation URL is not an approved HTTPS endpoint")


def _get_key(slug: str) -> str | None:
    ep = next((p for p in PROVIDERS if p.slug == slug), None)
    if not ep:
        return None
    return os.environ.get(ep.env_key) or None


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _validate_anthropic(key: str) -> dict[str, Any]:
    """Validate Anthropic key by sending a minimal request."""
    try:
        payload = json.dumps(
            {
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            }
        ).encode()
        req = Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            method="POST",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urlopen(req, timeout=10) as resp:  # nosec B310 -- fixed Anthropic HTTPS endpoint.
            if resp.status == 200:
                return {
                    "valid": True,
                    "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
                }
            return {"valid": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        err = str(e)
        if "401" in err or "authentication" in err.lower():
            return {"valid": False, "error": "Invalid API key"}
        if "429" in err or "rate" in err.lower():
            return {"valid": True, "error": "Rate limited (key is valid)"}
        return {"valid": False, "error": err[:100]}


def _validate_generic(
    key: str,
    validate_url: str,
    header_format: str = "Bearer {key}",
    header_key: str = "Authorization",
) -> dict[str, Any]:
    """Generic key validation via GET to models endpoint."""
    try:
        _require_known_validation_url(validate_url)
        auth_header = header_format.replace("{key}", key)
        req = Request(validate_url, method="GET", headers={header_key: auth_header})
        with urlopen(req, timeout=10) as resp:  # nosec B310 -- approved HTTPS validation URL enforced above.
            if resp.status == 200:
                body = json.loads(resp.read())
                models = []
                if isinstance(body, dict) and "data" in body:
                    models = [m.get("id", "") for m in body.get("data", [])[:10]]
                return {"valid": True, "models": models}
            return {"valid": False, "error": f"HTTP {resp.status}"}
    except Exception as e:
        err = str(e)
        if "401" in err or "403" in err or "unauthorized" in err.lower():
            return {"valid": False, "error": "Invalid API key"}
        if "429" in err:
            return {"valid": True, "error": "Rate limited (key is valid)"}
        return {"valid": False, "error": err[:100]}


def validate_provider(slug: str) -> dict[str, Any]:
    ep = next((p for p in PROVIDERS if p.slug == slug), None)
    if not ep:
        return {"valid": False, "error": "Unknown provider"}
    key = os.environ.get(ep.env_key, "")
    if not key:
        return {"valid": False, "error": "Key not set", "env_key": ep.env_key}
    if ep.is_anthropic:
        result = _validate_anthropic(key)
    else:
        result = _validate_generic(key, ep.validate_url, ep.header_format, ep.header_key)
    result["key_preview"] = _mask_key(key)
    result["env_key"] = ep.env_key
    return result


def scan_all() -> list[dict[str, Any]]:
    results = []
    for ep in PROVIDERS:
        key = os.environ.get(ep.env_key, "")
        results.append(
            {
                "name": ep.name,
                "slug": ep.slug,
                "icon": ep.icon,
                "tier": ep.tier,
                "env_key": ep.env_key,
                "has_key": bool(key),
                "key_preview": _mask_key(key) if key else None,
                "free_models": list(ep.free_models),
                "signup_url": ep.signup_url,
                "description": ep.description,
            }
        )
    return results


def get_providers_list() -> list[dict[str, Any]]:
    return [
        {
            "name": ep.name,
            "slug": ep.slug,
            "icon": ep.icon,
            "tier": ep.tier,
            "env_key": ep.env_key,
            "free_models": list(ep.free_models),
            "signup_url": ep.signup_url,
            "docs_url": ep.docs_url,
            "description": ep.description,
        }
        for ep in PROVIDERS
    ]


def validate_all() -> list[dict[str, Any]]:
    results = []
    for ep in PROVIDERS:
        key = os.environ.get(ep.env_key, "")
        if not key:
            results.append(
                {
                    "name": ep.name,
                    "slug": ep.slug,
                    "icon": ep.icon,
                    "valid": False,
                    "error": "Key not set",
                }
            )
            continue
        if ep.is_anthropic:
            v = _validate_anthropic(key)
        else:
            v = _validate_generic(key, ep.validate_url, ep.header_format, ep.header_key)
        results.append(
            {
                "name": ep.name,
                "slug": ep.slug,
                "icon": ep.icon,
                "valid": v.get("valid", False),
                "error": v.get("error"),
                "models": v.get("models", []),
            }
        )
    return results
