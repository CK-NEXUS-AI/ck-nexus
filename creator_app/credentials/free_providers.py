from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FreeProvider:
    """Hosted OpenAI-compatible provider candidate.

    ``free`` means a verified unlimited zero-cost entitlement, not merely a
    provider that advertises a free tier. No hosted provider below is guaranteed
    unlimited and free, so every entry defaults to ``False``. Unattended key-pool
    routing independently blocks all hosted endpoints.
    """

    id: str
    env_var: str
    base_url: str
    model: str
    free: bool = False


# Auto-discovered when the matching env var is present. CKNEXUS_LLM_KEYS takes
# precedence for full control (multiple keys per provider, custom models).
AUTO_DISCOVER_PROVIDERS: tuple[FreeProvider, ...] = (
    FreeProvider(
        "groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"
    ),
    FreeProvider("mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1", "mistral-small-latest"),
    FreeProvider("cerebras", "CEREBRAS_API_KEY", "https://api.cerebras.ai/v1", "llama-3.3-70b"),
    FreeProvider(
        "sambanova", "SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1", "Llama-3.3-70B-Instruct"
    ),
    FreeProvider(
        "openrouter",
        "OPENROUTER_API_KEY",
        "https://openrouter.ai/api/v1",
        "meta-llama/llama-3.3-70b-instruct:free",
    ),
    FreeProvider("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com/v1", "deepseek-chat"),
    FreeProvider(
        "together",
        "TOGETHER_API_KEY",
        "https://api.together.xyz/v1",
        "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    ),
    FreeProvider("zhipu", "ZHIPU_API_KEY", "https://open.bigmodel.cn/api/paas/v4", "glm-4-flash"),
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
        "moonshot", "MOONSHOT_API_KEY", "https://api.moonshot.cn/v1", "kimi-k2-0711-preview"
    ),
    FreeProvider("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4.1-mini"),
)
