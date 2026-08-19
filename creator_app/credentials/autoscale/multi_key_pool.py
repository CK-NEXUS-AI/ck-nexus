"""Multi-Key Pool — จัดการ API Key หลายตัว + Auto-Failover.

ระบบจัดการ key หลายตัวต่อ provider:
- เก็บ key หลายตัวใน vault
- ติดตามสถานะแต่ละตัว (active/dead/quarantine)
- สลับอัตโนมัติเมื่อตัวปัจจุบันพัง
- ถอดรหัส key โดยไม่เปิดเผยค่า

วิธีใช้:
    pool = MultiKeyPool()
    pool.add_key("postman", "PMAK-xxxxx")
    pool.add_key("postman", "PMAK-yyyyy")  # backup

    key = pool.get_key("postman")  # ได้ key ที่ยังใช้ได้
    pool.mark_dead(key.vault_id)   # ตัวนี้พัง
    key = pool.get_key("postman")  # สลับไปตัวถัดไปอัตโนมัติ
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

from creator_app.credentials.blind_vault import BlindVault


class KeyStatus(Enum):
    ACTIVE = "active"
    DEAD = "dead"
    QUARANTINE = "quarantine"
    PROVISIONING = "provisioning"


@dataclass
class PoolEntry:
    """key หนึ่งตัวใน pool."""

    vault_id: str
    provider: str
    status: KeyStatus = KeyStatus.ACTIVE
    fail_count: int = 0
    last_used: float = 0.0
    last_fail: float = 0.0
    last_success: float = 0.0
    total_calls: int = 0
    success_rate: float = 1.0
    tags: tuple[str, ...] = ()


class MultiKeyPool:
    """จัดการ API Key หลายตัว + Auto-Failover.

    วิธีใช้:
        pool = MultiKeyPool()
        pool.add_key("postman", "PMAK-key1")
        pool.add_key("postman", "PMAK-key2")

        # ใช้งาน — ได้ key ที่ยังใช้ได้
        entry = pool.get_key("postman")
        if entry:
            key_value = pool.retrieve(entry.vault_id)
            result = call_api(key_value)

            if success:
                pool.mark_success(entry.vault_id)
            else:
                pool.mark_dead(entry.vault_id)
                entry = pool.get_key("postman")  # auto-failover
    """

    MAX_FAILS = 3
    QUARANTINE_DURATION = 3600  # 1 ชั่วโมง

    def __init__(self, vault_dir: str | None = None):
        self._vault = BlindVault(vault_dir=vault_dir)
        self._pools: dict[str, list[PoolEntry]] = {}
        self._event_log: list[dict] = []

    def add_key(self, provider: str, key: str, *, tags: tuple[str, ...] = ()) -> str:
        """เพิ่ม key ใหม่เข้า pool — return vault_id."""
        vid = self._vault.store(provider, key, tags=tags)
        entry = PoolEntry(vault_id=vid, provider=provider, tags=tags)
        self._pools.setdefault(provider, []).append(entry)
        self._log_event("key_added", provider, vid)
        return vid

    def get_key(self, provider: str) -> PoolEntry | None:
        """ดึง key ที่ยังใช้ได้ — คืน PoolEntry (ไม่คืน key จริง)."""
        self._cleanup_quarantine(provider)
        pool = self._pools.get(provider, [])

        # คัดกรอง: เอาเฉพาะตัวที่ ACTIVE
        active = [e for e in pool if e.status == KeyStatus.ACTIVE]
        if not active:
            self._log_event("no_active_keys", provider)
            return None

        # เลือกตัวที่ success_rate สูงสุด + ใช้น้อยสุด
        active.sort(key=lambda e: (e.success_rate, -e.total_calls), reverse=True)
        entry = active[0]
        entry.last_used = time.time()
        entry.total_calls += 1
        return entry

    def get_key_value(self, provider: str) -> tuple[str, PoolEntry] | None:
        """ดึง key จริง + entry — สำหรับใช้งาน."""
        entry = self.get_key(provider)
        if not entry:
            return None
        key = self._vault.retrieve(entry.vault_id)
        return key, entry

    def mark_success(self, vault_id: str) -> None:
        """มาร์คว่าใช้สำเร็จ."""
        entry = self._find(vault_id)
        if entry:
            entry.last_success = time.time()
            entry.success_rate = min(1.0, entry.success_rate + 0.1)
            entry.fail_count = max(0, entry.fail_count - 1)

    def mark_dead(self, vault_id: str, reason: str = "") -> None:
        """มาร์คว่า key นี้พัง."""
        entry = self._find(vault_id)
        if not entry:
            return
        entry.fail_count += 1
        entry.last_fail = time.time()
        entry.success_rate = max(0.0, entry.success_rate - 0.3)

        if entry.fail_count >= self.MAX_FAILS:
            entry.status = KeyStatus.DEAD
            self._log_event("key_dead", entry.provider, vault_id, reason)
        else:
            entry.status = KeyStatus.QUARANTINE
            self._log_event("key_quarantined", entry.provider, vault_id, reason)

    def mark_active(self, vault_id: str) -> None:
        """มาร์คว่ากลับมาใช้ได้."""
        entry = self._find(vault_id)
        if entry:
            entry.status = KeyStatus.ACTIVE
            entry.fail_count = 0

    def remove_key(self, vault_id: str) -> bool:
        """ลบ key ออกจาก pool."""
        for provider, pool in self._pools.items():
            for i, entry in enumerate(pool):
                if entry.vault_id == vault_id:
                    pool.pop(i)
                    self._vault.delete(vault_id)
                    self._log_event("key_removed", provider, vault_id)
                    return True
        return False

    def list_keys(self, provider: str | None = None) -> list[dict]:
        """ดูรายการ key ทั้งหมด (ไม่เปิด key จริง)."""
        results = []
        for prov, pool in self._pools.items():
            if provider and prov != provider:
                continue
            for entry in pool:
                results.append({
                    "vault_id": entry.vault_id,
                    "provider": entry.provider,
                    "status": entry.status.value,
                    "fail_count": entry.fail_count,
                    "success_rate": round(entry.success_rate, 2),
                    "total_calls": entry.total_calls,
                })
        return results

    def status(self, provider: str | None = None) -> dict:
        """สถานะ pool."""
        total = 0
        active = 0
        dead = 0
        quarantine = 0
        for prov, pool in self._pools.items():
            if provider and prov != provider:
                continue
            for entry in pool:
                total += 1
                if entry.status == KeyStatus.ACTIVE:
                    active += 1
                elif entry.status == KeyStatus.DEAD:
                    dead += 1
                elif entry.status == KeyStatus.QUARANTINE:
                    quarantine += 1
        return {
            "total": total,
            "active": active,
            "dead": dead,
            "quarantine": quarantine,
        }

    def get_failover_chain(self, provider: str) -> list[str]:
        """ดูลำดับ failover ของ provider."""
        pool = self._pools.get(provider, [])
        active = [e for e in pool if e.status == KeyStatus.ACTIVE]
        active.sort(key=lambda e: e.success_rate, reverse=True)
        return [e.vault_id for e in active]

    # ─── Internal ───────────────────────────────────────

    def _find(self, vault_id: str) -> PoolEntry | None:
        for pool in self._pools.values():
            for entry in pool:
                if entry.vault_id == vault_id:
                    return entry
        return None

    def _cleanup_quarantine(self, provider: str) -> None:
        """ปลด quarantine ถ้าครบเวลา."""
        now = time.time()
        pool = self._pools.get(provider, [])
        for entry in pool:
            quarantine_expired = (
                entry.status == KeyStatus.QUARANTINE
                and now - entry.last_fail >= self.QUARANTINE_DURATION
            )
            if quarantine_expired:
                entry.status = KeyStatus.ACTIVE
                entry.fail_count = 0
                self._log_event("quarantine_released", provider, entry.vault_id)

    def _log_event(self, event: str, provider: str, vault_id: str = "", reason: str = "") -> None:
        self._event_log.append({
            "event": event,
            "provider": provider,
            "vault_id": vault_id,
            "reason": reason,
            "timestamp": time.time(),
        })

    @property
    def events(self) -> list[dict]:
        return list(self._event_log)
