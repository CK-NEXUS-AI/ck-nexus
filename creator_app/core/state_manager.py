"""State & Memory Orchestrator — จัดการสถานะ + ความจำทั้งหมด.

ไม่หาย ไม่ซ้ำซ้อน — persist ลงไฟล์ + in-memory cache
แยกจาก Vault (key) และ Intelligence (thinking)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StateEntry:
    """สถานะหนึ่งชิ้น."""

    key: str
    value: str | int | float | bool | dict | list
    category: str = "general"
    updated_at: float = 0.0
    version: int = 1


class StateManager:
    """State & Memory Orchestrator — จัดการสถานะทั้งหมด.

    วิธีใช้:
        state = StateManager()

        # ตั้งค่า
        state.set("current_task", "build dashboard")
        state.set("user_preference", {"lang": "th", "theme": "dark"})

        # ดึงค่า
        task = state.get("current_task")

        # ดูประวัติ
        history = state.history("current_task")
    """

    def __init__(self, state_dir: str | None = None):
        if state_dir is None:
            state_dir = str(Path.home() / ".ck-nexus" / "state")
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._states: dict[str, StateEntry] = {}
        self._history: dict[str, list[dict]] = {}
        self._load_all()

    def set(
        self,
        key: str,
        value: str | int | float | bool | dict | list,
        *,
        category: str = "general",
    ) -> None:
        """ตั้งค่าสถานะ — auto-save + version increment."""
        existing = self._states.get(key)
        version = (existing.version + 1) if existing else 1
        entry = StateEntry(
            key=key,
            value=value,
            category=category,
            updated_at=time.time(),
            version=version,
        )
        self._states[key] = entry
        self._history.setdefault(key, []).append({
            "value": value,
            "version": version,
            "timestamp": entry.updated_at,
        })
        self._save(key, entry)

    def get(
        self, key: str, default: str | None = None
    ) -> str | int | float | bool | dict | list | None:
        """ดึงค่าสถานะ."""
        entry = self._states.get(key)
        return entry.value if entry else default

    def delete(self, key: str) -> bool:
        """ลบสถานะ."""
        if key in self._states:
            del self._states[key]
            self._history.pop(key, None)
            f = self._dir / f"{key}.json"
            if f.exists():
                f.unlink()
            return True
        return False

    def history(self, key: str) -> list[dict]:
        """ดูประวัติการเปลี่ยนแปลง."""
        return list(self._history.get(key, []))

    def list_keys(self, category: str | None = None) -> list[str]:
        """ดูรายการ keys ทั้งหมด."""
        if category:
            return [
                k for k, v in self._states.items()
                if v.category == category
            ]
        return list(self._states.keys())

    def get_all(self, category: str | None = None) -> dict[str, StateEntry]:
        """ดึงทั้งหมด."""
        if category:
            return {
                k: v for k, v in self._states.items()
                if v.category == category
            }
        return dict(self._states)

    def stats(self) -> dict:
        """สถิติ."""
        categories: dict[str, int] = {}
        for entry in self._states.values():
            categories[entry.category] = categories.get(entry.category, 0) + 1
        return {
            "total_keys": len(self._states),
            "categories": categories,
            "total_history": sum(len(h) for h in self._history.values()),
        }

    def _save(self, key: str, entry: StateEntry) -> None:
        """บันทึกลงไฟล์."""
        f = self._dir / f"{key}.json"
        f.write_text(json.dumps({
            "key": entry.key,
            "value": entry.value,
            "category": entry.category,
            "updated_at": entry.updated_at,
            "version": entry.version,
        }, ensure_ascii=False, indent=2))

    def _load_all(self) -> None:
        """โหลดทั้งหมดจากไฟล์."""
        for f in self._dir.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                entry = StateEntry(**data)
                self._states[entry.key] = entry
            except (json.JSONDecodeError, TypeError):
                continue
