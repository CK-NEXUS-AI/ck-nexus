"""Local Model Bridge — เชื่อม Ollama/MLX/Local LLM เข้ากับ Coding Agent.

ทำให้ Codex/Claude Code ใช้ Local Model ได้โดยไม่ต้องแก้โค้ด
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LocalModel:
    """ข้อมูล local model หนึ่งตัว."""

    name: str
    provider: str  # ollama, mlx, llama.cpp, vllm
    size: str = ""
    available: bool = False
    endpoint: str = ""


class LocalModelBridge:
    """เชื่อม Local Models เข้ากับ Coding Agent.

    วิธีใช้:
        bridge = LocalModelBridge()
        models = bridge.discover()

        # ใช้ผ่าน OpenAI-compatible API
        endpoint = bridge.get_endpoint("llama3")
        # → http://localhost:11434/v1
    """

    def __init__(self) -> None:
        self._models: list[LocalModel] = []

    def discover(self) -> list[LocalModel]:
        """ค้นหา local models ทั้งหมด."""
        self._models = []
        self._discover_ollama()
        self._discover_mlx()
        self._discover_llamacpp()
        return self._models

    def get_endpoint(self, model_name: str) -> str | None:
        """ดึง endpoint ของ model."""
        for m in self._models:
            if m.name == model_name and m.available:
                return m.endpoint
        return None

    def get_openai_compatible_url(self) -> str | None:
        """ดึง URL แบบ OpenAI-compatible สำหรับ local models."""
        for m in self._models:
            if m.provider == "ollama" and m.available:
                return m.endpoint.replace("/api/chat", "/v1")
        return None

    def list_available(self) -> list[LocalModel]:
        """ดู models ที่พร้อมใช้งาน."""
        return [m for m in self._models if m.available]

    def status(self) -> dict:
        """สถานะ."""
        available = self.list_available()
        return {
            "total_models": len(self._models),
            "available": len(available),
            "providers": list(set(m.provider for m in available)),
        }

    def _discover_ollama(self) -> None:
        """ค้นหา Ollama models."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import requests
            resp = requests.get(f"{base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            for model in data.get("models", []):
                name = model.get("name", "")
                size = model.get("size", 0)
                size_str = f"{size // (1024*1024)}MB" if size else ""
                self._models.append(LocalModel(
                    name=name,
                    provider="ollama",
                    size=size_str,
                    available=True,
                    endpoint=f"{base_url}/api/chat",
                ))
        except Exception:
            self._models.append(LocalModel(
                name="llama3",
                provider="ollama",
                available=False,
                endpoint=f"{base_url}/api/chat",
            ))

    def _discover_mlx(self) -> None:
        """ค้นหา MLX models (macOS)."""
        mlx_path = os.path.expanduser("~/.cache/mlx")
        if os.path.exists(mlx_path):
            for item in os.listdir(mlx_path):
                if os.path.isdir(os.path.join(mlx_path, item)):
                    self._models.append(LocalModel(
                        name=item, provider="mlx", available=True,
                        endpoint="http://localhost:8080/v1",
                    ))

    def _discover_llamacpp(self) -> None:
        """ค้นหา llama.cpp server."""
        try:
            import requests
            resp = requests.get("http://localhost:8080/health", timeout=2)
            if resp.ok:
                self._models.append(LocalModel(
                    name="llamacpp-server",
                    provider="llama.cpp",
                    available=True,
                    endpoint="http://localhost:8080/v1",
                ))
        except Exception:
            pass
