"""AnyClaw Core — Super-Intelligent Chat Engine.

ลำดับการเรียก:
1. Cache (Redis/memory) → ถ้ามี → ตอบทันที
2. Free Providers (Groq, OpenRouter, HuggingFace, Gemini) → ถ้าได้ → ตอบ
3. Claude API (Anthropic) → ถ้าต้องการความฉลาดสูงสุด
4. Fallback (Ollama local) → ถ้าทุกอย่างล้ม

วิธีใช้:
    claw = AnyClawCore(mode="super")
    response = claw.chat("สร้าง Python script ดึง weather")
    print(response)
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class ChatResponse:
    """ผลลัพธ์จาก chat."""

    content: str
    provider: str
    model: str = ""
    latency_ms: float = 0.0
    from_cache: bool = False
    tokens_used: int = 0


class AnyClawCore:
    """Super-Intelligent Chat Engine.

    วิธีใช้:
        claw = AnyClawCore(mode="super")
        resp = claw.chat("สวัสดี")
        print(f"จาก {resp.provider}: {resp.content}")

        # ดูสถานะ
        status = claw.status()
    """

    FREE_PROVIDERS: list[dict] = [
        {
            "name": "groq",
            "env_key": "GROQ_API_KEY",
            "url": "https://api.groq.com/openai/v1/chat/completions",
            "model": "llama3-8b-8192",
            "headers_fn": lambda k: {"Authorization": f"Bearer {k}"},
        },
        {
            "name": "openrouter_free",
            "env_key": "OPENROUTER_API_KEY",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "model": "meta-llama/llama-3-8b-instruct:free",
            "headers_fn": lambda k: {
                "Authorization": f"Bearer {k}",
                "HTTP-Referer": "https://ck-nexus.local",
            },
        },
        {
            "name": "google_ai",
            "env_key": "GOOGLE_AI_STUDIO_KEY",
            "url": None,  # ใช้ google api ต่างออกไป
            "model": "gemini-1.5-flash",
        },
        {
            "name": "ollama_local",
            "env_key": "OLLAMA_BASE_URL",
            "url": None,  # local
            "model": "llama3",
        },
    ]

    CLAUDE_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, mode: str = "super"):
        """mode: 'super' = free → claude, 'free' = free only, 'claude' = claude only"""
        self.mode = mode
        self._cache: dict[str, str] = {}
        self._history: list[ChatResponse] = []
        self._call_count: dict[str, int] = {}

    def chat(self, message: str) -> ChatResponse:
        """ส่งข้อความ → ได้คำตอบ."""
        start = time.time()

        # 1. Cache check
        cached = self._cache.get(message)
        if cached:
            resp = ChatResponse(
                content=cached, provider="cache", from_cache=True,
                latency_ms=(time.time() - start) * 1000,
            )
            self._history.append(resp)
            return resp

        # 2. Mode-based routing
        if self.mode == "claude":
            resp = self._call_claude(message)
        elif self.mode == "free":
            resp = self._try_free_providers(message)
            if not resp:
                resp = ChatResponse(
                    content="⚠️ ไม่มี Free Provider ใดตอบกลับ — ลองตั้งค่า API key ใน .env",
                    provider="none",
                )
        else:  # super
            resp = self._try_free_providers(message)
            if not resp or not resp.content or "error" in resp.content.lower():
                resp = self._call_claude(message)

        resp.latency_ms = (time.time() - start) * 1000
        self._cache[message] = resp.content
        self._history.append(resp)
        self._call_count[resp.provider] = self._call_count.get(resp.provider, 0) + 1
        return resp

    def chat_stream(self, message: str):
        """Stream response — yield chunks."""
        resp = self.chat(message)
        for word in resp.content.split():
            yield word + " "

    def status(self) -> dict:
        """สถานะระบบ."""
        free_available = []
        for p in self.FREE_PROVIDERS:
            key = os.getenv(p["env_key"], "")
            if key:
                free_available.append(p["name"])
        claude_available = bool(os.getenv("ANTHROPIC_API_KEY", ""))
        return {
            "mode": self.mode,
            "cache_size": len(self._cache),
            "total_chats": len(self._history),
            "free_providers_available": free_available,
            "claude_available": claude_available,
            "calls_by_provider": self._call_count,
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    # ─── Free Providers ────────────────────────────────

    def _try_free_providers(self, message: str) -> ChatResponse | None:
        """ลองทุก free provider ทีละตัว."""

        for provider in self.FREE_PROVIDERS:
            name = provider["name"]
            env_key = provider.get("env_key", "")
            api_key = os.getenv(env_key, "")

            if not api_key:
                continue

            try:
                if name == "google_ai":
                    resp = self._call_google_ai(message, api_key, provider)
                elif name == "ollama_local":
                    resp = self._call_ollama(message, provider)
                else:
                    resp = self._call_openai_compatible(message, api_key, provider)

                if resp and resp.content:
                    return resp
            except Exception:
                continue

        return None

    def _call_openai_compatible(
        self, message: str, api_key: str, provider: dict,
    ) -> ChatResponse:
        """เรียก OpenAI-compatible API (Groq, OpenRouter)."""
        import requests
        headers = provider["headers_fn"](api_key)
        headers["Content-Type"] = "application/json"
        resp = requests.post(
            provider["url"],
            headers=headers,
            json={
                "model": provider["model"],
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return ChatResponse(
            content=content, provider=provider["name"],
            model=provider["model"], tokens_used=tokens,
        )

    def _call_google_ai(self, message: str, api_key: str, provider: dict) -> ChatResponse:
        """เรียก Google AI Studio (Gemini)."""
        import requests
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{provider['model']}:generateContent?key={api_key}"
        )
        resp = requests.post(
            url,
            json={"contents": [{"parts": [{"text": message}]}]},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        return ChatResponse(
            content=content, provider="google_ai",
            model=provider["model"],
        )

    def _call_ollama(self, message: str, provider: dict) -> ChatResponse:
        """เรียก Ollama local."""
        import requests
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        resp = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": provider["model"],
                "messages": [{"role": "user", "content": message}],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["message"]["content"]
        return ChatResponse(
            content=content, provider="ollama_local",
            model=provider["model"],
        )

    # ─── Claude API ────────────────────────────────────

    def _call_claude(self, message: str) -> ChatResponse:
        """เรียก Claude API (Anthropic)."""
        import requests
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            return ChatResponse(
                content="⚠️ ไม่มี ANTHROPIC_API_KEY — ตั้งค่าใน .env เพื่อใช้ Claude",
                provider="claude_unavailable",
            )
        try:
            resp = requests.post(
                self.CLAUDE_URL,
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": message}],
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            usage = data.get("usage", {})
            tokens = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            return ChatResponse(
                content=content, provider="claude",
                model="claude-3-5-sonnet", tokens_used=tokens,
            )
        except Exception as exc:
            return ChatResponse(
                content=f"❌ Claude Error: {exc}",
                provider="claude_error",
            )
