from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FreeProvider:
    """Provider preset with explicit zero-cost eligibility.

    ``free=True`` is intentionally rare. A provider having a free plan, signup
    promotion, or low price does not make every API key/request zero-cost: an
    account may be upgraded, a promotion may expire, or the selected model may
    be billed. Auto-discovery therefore defaults to ``free=False`` unless the
    exact route/model has a provider-published zero token price.

    Operator-defined ``CKNEXUS_LLM_KEYS`` remains the explicit override path
    when a deployment has separately verified a zero-cost commercial contract.
    """

    id: str
    env_var: str
    base_url: str
    model: str
    free: bool = False


# Auto-discovered when the matching env var is present. CKNEXUS_LLM_KEYS takes
# precedence for operator-controlled provider metadata.
#
# IMPORTANT: these are connectivity presets, not promises about billing tiers.
# Only OpenRouter's dedicated free router is marked zero-cost because that exact
# route is provider-published at zero prompt/completion token price. All other
# providers fail closed as paid/unknown even when they offer a Free Plan.
AUTO_DISCOVER_PROVIDERS: tuple[FreeProvider, ...] = (
    FreeProvider(
        "groq",
        "GROQ_API_KEY",
        "https://api.groq.com/openai/v1",
        "llama-3.3-70b-versatile",
    ),
    FreeProvider(
        "mistral",
        "MISTRAL_API_KEY",
        "https://api.mistral.ai/v1",
        "mistral-small-latest",
    ),
    FreeProvider(
        "cerebras",
        "CEREBRAS_API_KEY",
        "https://api.cerebras.ai/v1",
        "llama-3.3-70b",
    ),
    FreeProvider(
        "sambanova",
        "SAMBANOVA_API_KEY",
        "https://api.sambanova.ai/v1",
        "Llama-3.3-70B-Instruct",
    ),
    FreeProvider(
        "openrouter",
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/api/v1",
        "openrouter/free",
        free=True,
    ),
    FreeProvider(
        "deepseek",
        "DEEPSEEK_API_KEY",
        "https://api.deepseek.com/v1",
        "deepseek-chat",
    ),
    FreeProvider(
        "together",
        "TOGETHER_API_KEY",
        "https://api.together.xyz/v1",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    ),
    FreeProvider(
        "zhipu",
        "ZHIPU_API_KEY",
        "https://open.bigmodel.cn/api/paas/v4",
        "glm-4-flash",
    ),
    FreeProvider(
        "qwen",
        "DASHSCOPE_API_KEY",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-turbo",
    ),
    FreeProvider(
        "gemini",
        "GEMINI_API_KEY",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-2.5-flash",
    ),
    FreeProvider(
        "moonshot",
        "MOONSHOT_API_KEY",
        "https://api.moonshot.cn/v1",
        "kimi-k2-0711-preview",
    ),
    FreeProvider(
        "openai",
        "OPENAI_API_KEY",
        "https://api.openai.com/v1",
        "gpt-4.1-mini",
    ),
)
