"""Groq Adapter — เชื่อมต่อ Groq (เร็วสุด ~42ms)."""

from __future__ import annotations

import os
import time

from creator_app.connectors.providers.base import ProviderAdapter, ProviderResponse


class GroqAdapter(ProviderAdapter):
    """Groq — fastest LLM provider, free tier available."""

    @property
    def name(self) -> str:
        return "groq"

    @property
    def env_key(self) -> str:
        return "GROQ_API_KEY"

    def chat(
        self,
        message: str,
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        import requests
        api_key = os.getenv(self.env_key, "")
        if not api_key:
            return ProviderResponse(
                content="", model="unknown", provider=self.name,
                success=False, error="GROQ_API_KEY not set",
            )
        model = model or "llama3-8b-8192"
        start = time.time()
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "max_tokens": max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return ProviderResponse(
                content=content, model=model, provider=self.name,
                tokens_used=tokens, latency_ms=latency,
            )
        except Exception as exc:
            return ProviderResponse(
                content="", model=model, provider=self.name,
                success=False, error=str(exc),
            )
