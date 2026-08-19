"""Key Health Monitor — ตรวจสอบสถานะ key ทุกตัวอัตโนมัติ.

- ตรวจสอบ key ทุกตัวเป็นระยะ
- ติดตาม success rate, latency, error patterns
- แจ้งเตือนเมื่อ key ใกล้พัง
- แนะนำ action (swap, rotate, deprovision)
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class HealthCheckResult:
    """ผลตรวจสุขภาพของ key หนึ่งตัว."""

    vault_id: str
    provider: str
    healthy: bool
    latency_ms: float = 0.0
    error: str = ""
    checked_at: float = 0.0
    recommendation: str = ""


@dataclass
class ProviderHealth:
    """สถานะสุขภาพรวมของ provider."""

    provider: str
    total_keys: int = 0
    active_keys: int = 0
    dead_keys: int = 0
    avg_success_rate: float = 0.0
    needs_new_key: bool = False
    recommendation: str = ""


class KeyHealthMonitor:
    """ตรวจสอบสุขภาพ key อัตโนมัติ.

    วิธีใช้:
        monitor = KeyHealthMonitor(pool)

        # ตรวจ key ตัวเดียว
        result = monitor.check_key(entry)
        if not result.healthy:
            pool.mark_dead(entry.vault_id, result.error)

        # ตรวจทั้ง pool
        report = monitor.full_check()
        for provider, health in report.items():
            if health.needs_new_key:
                print(f"⚠️ {provider} ต้องการ key ใหม่!")
    """

    def __init__(self, pool: object | None = None):
        self._pool = pool
        self._results: list[HealthCheckResult] = []
        self._checks: dict[str, list[HealthCheckResult]] = {}

    def check_key(self, entry: object) -> HealthCheckResult:
        """ตรวจสุขภาพ key หนึ่งตัว."""
        vault_id = getattr(entry, "vault_id", "unknown")
        provider = getattr(entry, "provider", "unknown")
        success_rate = getattr(entry, "success_rate", 1.0)
        fail_count = getattr(entry, "fail_count", 0)
        total_calls = getattr(entry, "total_calls", 0)

        healthy = True
        recommendation = "keep"
        latency_ms = 0.0
        error = ""

        # ตรวจสอบ success rate
        if success_rate < 0.3:
            healthy = False
            recommendation = "deprovision"
            error = f"Low success rate: {success_rate:.0%}"
        elif success_rate < 0.7:
            recommendation = "monitor_closely"

        # ตรวจสอบ fail count
        if fail_count >= 3:
            healthy = False
            recommendation = "swap"
            error = f"Too many failures: {fail_count}"
        elif fail_count >= 2:
            recommendation = "monitor"

        # ตรวจสอบว่าไม่เคยใช้
        if total_calls == 0:
            recommendation = "test_first"

        result = HealthCheckResult(
            vault_id=vault_id,
            provider=provider,
            healthy=healthy,
            latency_ms=latency_ms,
            error=error,
            checked_at=time.time(),
            recommendation=recommendation,
        )
        self._results.append(result)
        self._checks.setdefault(provider, []).append(result)
        return result

    def full_check(self) -> dict[str, ProviderHealth]:
        """ตรวจทั้ง pool — return สถานะรวมต่อ provider."""
        if self._pool is None:
            return {}

        provider_stats: dict[str, dict] = {}
        keys = self._pool.list_keys() if hasattr(self._pool, "list_keys") else []

        for key_info in keys:
            prov = key_info.get("provider", "unknown")
            if prov not in provider_stats:
                provider_stats[prov] = {
                    "total": 0, "active": 0, "dead": 0, "rates": [],
                }
            stats = provider_stats[prov]
            stats["total"] += 1
            if key_info.get("status") == "active":
                stats["active"] += 1
                stats["rates"].append(key_info.get("success_rate", 1.0))
            elif key_info.get("status") == "dead":
                stats["dead"] += 1

        report: dict[str, ProviderHealth] = {}
        for prov, stats in provider_stats.items():
            avg_rate = sum(stats["rates"]) / len(stats["rates"]) if stats["rates"] else 0.0
            needs_new = stats["active"] < 2 or avg_rate < 0.5
            rec = "ok"
            if stats["active"] == 0:
                rec = "URGENT: provision new key"
            elif stats["active"] == 1:
                rec = "WARNING: only 1 active key — add backup"
            elif avg_rate < 0.5:
                rec = "WARNING: low success rate — add backup"
            report[prov] = ProviderHealth(
                provider=prov,
                total_keys=stats["total"],
                active_keys=stats["active"],
                dead_keys=stats["dead"],
                avg_success_rate=avg_rate,
                needs_new_key=needs_new,
                recommendation=rec,
            )
        return report

    def get_recommendation(self, provider: str) -> str:
        """แนะนำ action สำหรับ provider."""
        has_pool = self._pool and hasattr(self._pool, "status")
        pool_status = self._pool.status(provider) if has_pool else {}
        active = pool_status.get("active", 0)
        dead = pool_status.get("dead", 0)

        if active == 0:
            return "🚨 CRITICAL: ต้องสร้าง key ใหม่ทันที"
        if active == 1 and dead > 0:
            return "⚠️ WARNING: เหลือ key เดียว — เพิ่ม backup ด่วน"
        if active == 1:
            return "⚠️ CAUTION: ไม่มี backup — เพิ่ม key สำรอง"
        return "✅ OK: มี key พร้อมใช้งานเพียงพอ"

    @property
    def recent_results(self) -> list[HealthCheckResult]:
        return list(self._results[-50:])
