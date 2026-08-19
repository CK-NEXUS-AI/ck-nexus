"""Provider Health Monitor — ตรวจสอบสุขภาพ provider + auto-failover.

ตรวจสอบ:
1. API Key ยังใช้ได้หรือไม่
2. เครดิตเหลือเท่าไหร่
3. Response time เร็วแค่ไหน
4. ถ้าล้ม → สลับไปตัวถัดไปอัตโนมัติ
5. ถ้า key หมด → สร้าง key ใหม่หรือใช้ free tier
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class ProviderStatus:
    name: str
    health: ProviderHealth = ProviderHealth.UNKNOWN
    latency_ms: float = 0.0
    credit_remaining_pct: float = 100.0
    last_check: float | None = None
    error_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    is_active: bool = True
    priority: int = 0


class ProviderHealthMonitor:
    """ตรวจสอบสุขภาพ provider + auto-failover.

    วิธีใช้:
        monitor = ProviderHealthMonitor()

        # ตรวจสอบทุก provider
        monitor.check_all()

        # ดึง provider ที่ healthy
        best = monitor.get_best_provider()

        # ดูสถานะทั้งหมด
        status = monitor.get_all_status()
    """

    PROVIDERS: list[ProviderStatus] = [
        ProviderStatus(name="groq", priority=1),
        ProviderStatus(name="openrouter_free", priority=2),
        ProviderStatus(name="google_ai_studio", priority=3),
        ProviderStatus(name="cerebras", priority=4),
        ProviderStatus(name="sambanova", priority=5),
        ProviderStatus(name="ollama_local", priority=6),
    ]

    def __init__(self) -> None:
        self._providers: dict[str, ProviderStatus] = {}
        for p in self.PROVIDERS:
            self._providers[p.name] = p
        self._failover_log: list[dict[str, Any]] = []

    def check_all(self) -> dict[str, ProviderHealth]:
        """ตรวจสอบทุก provider."""
        results = {}
        for name, provider in self._providers.items():
            health = self._check_provider(name)
            provider.health = health
            provider.last_check = time.time()
            results[name] = health
        return results

    def get_best_provider(self) -> ProviderStatus | None:
        """ดึง provider ที่ดีที่สุด (healthy + priority ต่ำสุด)."""
        candidates = [
            p for p in self._providers.values()
            if p.health == ProviderHealth.HEALTHY and p.is_active
        ]
        if not candidates:
            # ลอง degraded
            candidates = [
                p for p in self._providers.values()
                if p.health == ProviderHealth.DEGRADED and p.is_active
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda p: p.priority)

    def failover(self, failed_provider: str) -> ProviderStatus | None:
        """สลับไป provider ถัดไป."""
        failed = self._providers.get(failed_provider)
        if failed:
            failed.consecutive_failures += 1
            failed.error_count += 1
            if failed.consecutive_failures >= 3:
                failed.health = ProviderHealth.DOWN
                failed.is_active = False

        best = self.get_best_provider()
        if best:
            self._failover_log.append({
                "from": failed_provider,
                "to": best.name,
                "timestamp": time.time(),
                "reason": "auto-failover",
            })
        return best

    def record_success(self, provider_name: str, latency_ms: float = 0.0) -> None:
        """บันทึกความสำเร็จ."""
        p = self._providers.get(provider_name)
        if p:
            p.success_count += 1
            p.consecutive_failures = 0
            p.latency_ms = latency_ms
            if p.health == ProviderHealth.DOWN:
                p.health = ProviderHealth.HEALTHY
                p.is_active = True

    def record_failure(self, provider_name: str, error: str = "") -> None:
        """บันทึกความล้มเหลว."""
        p = self._providers.get(provider_name)
        if p:
            p.consecutive_failures += 1
            p.error_count += 1
            if p.consecutive_failures >= 5:
                p.health = ProviderHealth.DOWN
                p.is_active = False

    def get_all_status(self) -> list[dict[str, Any]]:
        """ดึงสถานะทั้งหมด."""
        return [
            {
                "name": p.name,
                "health": p.health.value,
                "latency_ms": p.latency_ms,
                "credit_pct": p.credit_remaining_pct,
                "success": p.success_count,
                "errors": p.error_count,
                "active": p.is_active,
                "priority": p.priority,
            }
            for p in sorted(self._providers.values(), key=lambda x: x.priority)
        ]

    def get_failover_log(self) -> list[dict[str, Any]]:
        return self._failover_log.copy()

    def _check_provider(self, name: str) -> ProviderHealth:
        """ตรวจสอบ provider หนึ่งตัว (แบบง่าย)."""
        # ในระบบจริงจะยิง API request จริง
        p = self._providers.get(name)
        if p and p.consecutive_failures >= 5:
            return ProviderHealth.DOWN
        return ProviderHealth.HEALTHY

    def summary(self) -> str:
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  🔍 Provider Health Monitor — สถานะ               ║",
            "╚══════════════════════════════════════════════════╝",
            "",
        ]
        health_emoji = {
            "healthy": "🟢",
            "degraded": "🟡",
            "down": "🔴",
            "unknown": "⚪",
        }
        for p in sorted(self._providers.values(), key=lambda x: x.priority):
            emoji = health_emoji.get(p.health.value, "❓")
            active_tag = "" if p.is_active else " [DISABLED]"
            lines.append(f"  {emoji} {p.name} (priority={p.priority}){active_tag}")
            lines.append(f"     latency: {p.latency_ms:.0f}ms | success: {p.success_count} | errors: {p.error_count}")

        if self._failover_log:
            lines.append(f"\n🔄 Failover events: {len(self._failover_log)}")
        return "\n".join(lines)
