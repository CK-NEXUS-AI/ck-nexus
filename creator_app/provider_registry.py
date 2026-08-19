from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ProviderTier(StrEnum):
    FREE = "free"
    FREEMIUM = "freemium"
    PAID = "paid"


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    name: str
    slug: str
    base_url: str
    env_key: str
    tier: ProviderTier
    header_format: str = "Bearer {key}"
    key_validation_endpoint: str = ""
    key_validation_method: str = "GET"
    models_endpoint: str = ""
    free_models: tuple[str, ...] = ()
    signup_url: str = ""
    docs_url: str = ""
    description: str = ""
    icon: str = ""


PROVIDER_REGISTRY: list[ProviderSpec] = [
    ProviderSpec(
        name="Groq",
        slug="groq",
        base_url="https://api.groq.com/openai/v1",
        env_key="GROQ_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.groq.com/openai/v1/models",
        free_models=(
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemma2-9b-it",
            "mixtral-8x7b-32768",
        ),
        signup_url="https://console.groq.com/keys",
        docs_url="https://console.groq.com/docs",
        description="Fast inference, generous free tier",
        icon="⚡",
    ),
    ProviderSpec(
        name="Cerebras",
        slug="cerebras",
        base_url="https://api.cerebras.ai/v1",
        env_key="CEREBRAS_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.cerebras.ai/v1/models",
        free_models=(
            "llama-3.3-70b",
            "llama-3.1-8b",
        ),
        signup_url="https://cloud.cerebras.ai/",
        docs_url="https://inference-docs.cerebras.ai/",
        description="Ultra-fast inference speeds",
        icon="🧠",
    ),
    ProviderSpec(
        name="OpenRouter",
        slug="openrouter",
        base_url="https://openrouter.ai/api/v1",
        env_key="OPENROUTER_API_KEY",
        tier=ProviderTier.FREE,
        header_format="Bearer {key}",
        key_validation_endpoint="https://openrouter.ai/api/v1/models",
        free_models=(
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-9b-it:free",
            "mistralai/mistral-7b-instruct:free",
            "qwen/qwen-2.5-72b-instruct:free",
        ),
        signup_url="https://openrouter.ai/keys",
        docs_url="https://openrouter.ai/docs",
        description="Gateway to 100+ models, many free",
        icon="🔀",
    ),
    ProviderSpec(
        name="Google Gemini",
        slug="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        env_key="GEMINI_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        free_models=(
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ),
        signup_url="https://aistudio.google.com/apikey",
        docs_url="https://ai.google.dev/docs",
        description="Google's latest models, free tier",
        icon="💎",
    ),
    ProviderSpec(
        name="DeepSeek",
        slug="deepseek",
        base_url="https://api.deepseek.com/v1",
        env_key="DEEPSEEK_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.deepseek.com/v1/models",
        free_models=(
            "deepseek-chat",
            "deepseek-reasoner",
        ),
        signup_url="https://platform.deepseek.com/",
        docs_url="https://platform.deepseek.com/api-docs",
        description="Strong reasoning, free credits",
        icon="🔍",
    ),
    ProviderSpec(
        name="Together AI",
        slug="together",
        base_url="https://api.together.xyz/v1",
        env_key="TOGETHER_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.together.xyz/v1/models",
        free_models=(
            "meta-llama/Llama-3-70b-chat-hf",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ),
        signup_url="https://api.together.xyz/settings/api-keys",
        docs_url="https://docs.together.ai/",
        description="Open-source model hosting, free credits",
        icon="🤝",
    ),
    ProviderSpec(
        name="Mistral AI",
        slug="mistral",
        base_url="https://api.mistral.ai/v1",
        env_key="MISTRAL_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.mistral.ai/v1/models",
        free_models=(
            "mistral-small-latest",
            "mistral-tiny",
        ),
        signup_url="https://console.mistral.ai/api-keys/",
        docs_url="https://docs.mistral.ai/",
        description="European AI, free tier available",
        icon="🌊",
    ),
    ProviderSpec(
        name="SambaNova",
        slug="sambanova",
        base_url="https://api.sambanova.ai/v1",
        env_key="SAMBANOVA_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.sambanova.ai/v1/models",
        free_models=(
            "Meta-Llama-3.3-70B-Instruct",
            "DeepSeek-V3-0324",
        ),
        signup_url="https://cloud.sambanova.ai/apis",
        docs_url="https://docs.sambanova.ai/",
        description="Enterprise-grade, free tier",
        icon="🔥",
    ),
    ProviderSpec(
        name="Fireworks AI",
        slug="fireworks",
        base_url="https://api.fireworks.ai/inference/v1",
        env_key="FIREWORKS_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.fireworks.ai/inference/v1/models",
        free_models=("accounts/fireworks/models/llama-v3p3-70b-instruct",),
        signup_url="https://fireworks.ai/account/api-keys",
        docs_url="https://docs.fireworks.ai/",
        description="Fast inference, free tier",
        icon="🎆",
    ),
    ProviderSpec(
        name="Cloudflare Workers AI",
        slug="cloudflare",
        base_url="https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        env_key="CLOUDFLARE_API_TOKEN",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.cloudflare.com/client/v4/user/tokens/verify",
        free_models=(
            "@cf/meta/llama-3.3-70b-instruct-fp8",
            "@cf/qwen/qwen1.5-14b-chat-awq",
        ),
        signup_url="https://dash.cloudflare.com/profile/api-tokens",
        docs_url="https://developers.cloudflare.com/workers-ai/",
        description="Edge AI, generous free tier",
        icon="☁️",
    ),
    ProviderSpec(
        name="xAI (Grok)",
        slug="xai",
        base_url="https://api.x.ai/v1",
        env_key="XAI_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.x.ai/v1/models",
        free_models=("grok-2-1212",),
        signup_url="https://console.x.ai/",
        docs_url="https://docs.x.ai/",
        description="Elon Musk's AI, free credits",
        icon="✖️",
    ),
    ProviderSpec(
        name="Cohere",
        slug="cohere",
        base_url="https://api.cohere.com/v2",
        env_key="COHERE_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.cohere.com/v2/models",
        free_models=(
            "command-r",
            "command-r-plus",
        ),
        signup_url="https://dashboard.cohere.com/api-keys",
        docs_url="https://docs.cohere.com/",
        description="RAG-optimized, free tier",
        icon="📊",
    ),
    ProviderSpec(
        name="Novita AI",
        slug="novita",
        base_url="https://api.novita.ai/v3/openai",
        env_key="NOVITA_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.novita.ai/v3/openai/models",
        free_models=("meta-llama/llama-3.3-70b-instruct",),
        signup_url="https://novita.ai/settings",
        docs_url="https://novita.ai/docs",
        description="Uncensored models, free tier",
        icon="🚀",
    ),
    ProviderSpec(
        name="Chutes AI",
        slug="chutes",
        base_url="https://api.chutes.ai/v1",
        env_key="CHUTES_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://api.chutes.ai/v1/models",
        free_models=("chutesai/llama-3.3-70b-instruct",),
        signup_url="https://chutes.ai/app/api-keys",
        docs_url="https://chutes.ai/docs",
        description="Community-driven, free tier",
        icon="🪂",
    ),
    ProviderSpec(
        name="HuggingFace",
        slug="huggingface",
        base_url="https://api-inference.huggingface.co/v1",
        env_key="HUGGINGFACE_API_KEY",
        tier=ProviderTier.FREE,
        key_validation_endpoint="https://huggingface.co/api/whoami-v2",
        free_models=(
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen2.5-72B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
        ),
        signup_url="https://huggingface.co/settings/tokens",
        docs_url="https://huggingface.co/docs/api-inference/",
        description="Open-source hub, free inference",
        icon="🤗",
    ),
    ProviderSpec(
        name="OpenAI",
        slug="openai",
        base_url="https://api.openai.com/v1",
        env_key="OPENAI_API_KEY",
        tier=ProviderTier.FREEMIUM,
        key_validation_endpoint="https://api.openai.com/v1/models",
        free_models=("gpt-4o-mini",),
        signup_url="https://platform.openai.com/api-keys",
        docs_url="https://platform.openai.com/docs",
        description="$5 free credit on signup",
        icon="🤖",
    ),
    ProviderSpec(
        name="Anthropic",
        slug="anthropic",
        base_url="https://api.anthropic.com/v1",
        env_key="ANTHROPIC_API_KEY",
        tier=ProviderTier.FREEMIUM,
        key_validation_endpoint="https://api.anthropic.com/v1/messages",
        free_models=("claude-3-5-haiku-20241022",),
        signup_url="https://console.anthropic.com/settings/keys",
        docs_url="https://docs.anthropic.com/",
        description="Claude models, free tier",
        icon="🏛️",
    ),
]


def get_all_providers() -> list[dict[str, Any]]:
    return [
        {
            "name": p.name,
            "slug": p.slug,
            "tier": p.tier,
            "icon": p.icon,
            "description": p.description,
            "signup_url": p.signup_url,
            "docs_url": p.docs_url,
            "free_models": list(p.free_models),
            "env_key": p.env_key,
        }
        for p in PROVIDER_REGISTRY
    ]


def get_provider_by_slug(slug: str) -> ProviderSpec | None:
    for p in PROVIDER_REGISTRY:
        if p.slug == slug:
            return p
    return None


def validate_key_from_env(slug: str) -> dict[str, Any]:
    spec = get_provider_by_slug(slug)
    if not spec:
        return {"valid": False, "error": "Unknown provider"}
    key = os.environ.get(spec.env_key, "")
    if not key:
        return {"valid": False, "error": "Key not set", "env_key": spec.env_key}
    return {
        "valid": True,
        "env_key": spec.env_key,
        "key_preview": f"****{key[-4:]}" if len(key) > 4 else "****",
    }


def scan_all_providers() -> list[dict[str, Any]]:
    results = []
    for p in PROVIDER_REGISTRY:
        key = os.environ.get(p.env_key, "")
        results.append(
            {
                "name": p.name,
                "slug": p.slug,
                "icon": p.icon,
                "tier": p.tier,
                "env_key": p.env_key,
                "has_key": bool(key),
                "key_preview": f"****{key[-4:]}" if len(key) > 4 else None,
            }
        )
    return results
