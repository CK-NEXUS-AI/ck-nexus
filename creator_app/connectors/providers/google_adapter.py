"""Google AI Studio Adapter — เชื่อมต่อ Gemini."""

from __future__ import annotations

import os
import time

from creator_app.connectors.providers.base import ProviderAdapter, ProviderResponse


class GoogleAdapter(ProviderAdapter):
    """Google AI Studio — Gemini 1.5 Flash/Pro."""

    @property
    def name(self) -> str:
        return "google_ai"

    @property
    def env_key(self) -> str:
        return "GOOGLE_AI_STUDIO_KEY"

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
                success=False, error="GOOGLE_AI_STUDIO_KEY not set",
            )
        model = model or "gemini-1.5-flash"
        start = time.time()
        try:
            url = (
                f"https://generativelanguage.googleapis.com/v1beta/"
                f"models/{model}:generateContent?key={api_key}"
            )
            resp = requests.post(
                url,
                json={"contents": [{"parts": [{"text": message}]}]},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            latency = (time.time() - start) * 1000
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return ProviderResponse(
                content=content, model=model, provider=self.name,
                latency_ms=latency,
            )
        except Exception as exc:
            return ProviderResponse(
                content="", model=model, provider=self.name,
                success=False, error=str(exc),
            )
