"""Ollama Adapter — เชื่อมต่อ Local LLM (ฟรี 100%)."""

from __future__ import annotations

import os
import time

from creator_app.connectors.providers.base import ProviderAdapter, ProviderResponse


class OllamaAdapter(ProviderAdapter):
    """Ollama — run LLM locally, 100% free, unlimited."""

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def env_key(self) -> str:
        return "OLLAMA_BASE_URL"

    def chat(
        self,
        message: str,
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        import requests
        base_url = os.getenv(self.env_key, "http://localhost:11434")
        model = model or "llama3"
        start = time.time()
        try:
            resp = requests.post(
                f"{base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": message}],
                    "stream": False,
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            content = data["message"]["content"]
            return ProviderResponse(
                content=content, model=model, provider=self.name,
                latency_ms=latency,
            )
        except Exception as exc:
            return ProviderResponse(
                content="", model=model, provider=self.name,
                success=False, error=str(exc),
            )
