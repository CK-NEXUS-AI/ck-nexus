"""SD Card / Local Storage Manager — เก็บข้อมูลขนาดใหญ่.

เก็บ offline ได้ — แยกจากระบบหลัก — ไม่ขึ้นกับ cloud
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class SDCardManager:
    """จัดการข้อมูลบน SD Card / Local Storage.

    วิธีใช้:
        storage = SDCardManager("/sdcard/ck-nexus")
        storage.save("logs", "2024-01-01", {"events": [...]})
        data = storage.load("logs", "2024-01-01")
    """

    def __init__(self, base_path: str | None = None):
        if base_path is None:
            base_path = os.path.expanduser("~/.ck-nexus/storage")
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def save(self, namespace: str, key: str, data: dict | list | str) -> str:
        """บันทึกข้อมูล — return file path."""
        ns_dir = self._base / namespace
        ns_dir.mkdir(exist_ok=True)
        fpath = ns_dir / f"{key}.json"
        content = json.dumps(data, ensure_ascii=False, indent=2)
        fpath.write_text(content)
        return str(fpath)

    def load(self, namespace: str, key: str) -> dict | list | None:
        """ดึงข้อมูล."""
        fpath = self._base / namespace / f"{key}.json"
        if not fpath.exists():
            return None
        try:
            return json.loads(fpath.read_text())
        except (json.JSONDecodeError, TypeError):
            return None

    def list_keys(self, namespace: str) -> list[str]:
        """ดู keys ทั้งหมดใน namespace."""
        ns_dir = self._base / namespace
        if not ns_dir.exists():
            return []
        return [f.stem for f in ns_dir.glob("*.json")]

    def delete(self, namespace: str, key: str) -> bool:
        """ลบข้อมูล."""
        fpath = self._base / namespace / f"{key}.json"
        if fpath.exists():
            fpath.unlink()
            return True
        return False

    def namespace_size(self, namespace: str) -> int:
        """ขนาดข้อมูลใน namespace (bytes)."""
        ns_dir = self._base / namespace
        if not ns_dir.exists():
            return 0
        return sum(f.stat().st_size for f in ns_dir.glob("*.json"))

    def stats(self) -> dict:
        """สถิติ."""
        namespaces: dict[str, int] = {}
        for ns_dir in self._base.iterdir():
            if ns_dir.is_dir():
                namespaces[ns_dir.name] = len(list(ns_dir.glob("*.json")))
        total_size = sum(self.namespace_size(ns) for ns in namespaces)
        return {
            "total_namespaces": len(namespaces),
            "total_files": sum(namespaces.values()),
            "total_size_bytes": total_size,
            "namespaces": namespaces,
        }
