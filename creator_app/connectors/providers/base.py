"""Base Provider Adapter — interface สำหรับทุก provider."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    """ผลลัพธ์จาก provider."""

    content: str
    model: str
    provider: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str = ""


class ProviderAdapter(ABC):
    """Interface สำหรับ Provider Adapter ทุกตัว."""

    @property
    @abstractmethod
    def name(self) -> str:
        """ชื่อ provider."""

    @property
    @abstractmethod
    def env_key(self) -> str:
        """ชื่อ environment variable สำหรับ key."""

    @abstractmethod
    def chat(
        self,
        message: str,
        *,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> ProviderResponse:
        """ส่งข้อความ → ได้คำตอบ."""

    def is_available(self) -> bool:
        """ตรวจสอบว่า provider พร้อมใช้งาน."""
        import os
        return bool(os.getenv(self.env_key))

    def health_check(self) -> dict:
        """ตรวจสุขภาพ provider."""
        return {
            "provider": self.name,
            "available": self.is_available(),
            "env_key": self.env_key,
        }
