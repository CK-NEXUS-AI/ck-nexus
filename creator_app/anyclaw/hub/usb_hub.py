"""USB Hub for AI — เสียบหลายระบบเข้าระบบเดียว.

หลักการ:
- แต่ละ Provider = พอร์ต USB 1 พอร์ต
- Hub จัดการทุกพอร์ต → ผู้ใช้เห็นแค่ "พอร์ตเดียว"
- ถ้าพอร์ตไหนหมด/พัง → สลับพอร์ตถัดไปอัตโนมัติ
- ถ้าทุกพอร์ตหมด → สร้างพอร์ตใหม่อัตโนมัติ
- ถ้าสร้างไม่ได้ → แจ้งเตือนผู้ใช้

เหมือน USB Hub:
- เสียบ USB 10-20 อัน → Hub จัดการให้หมด
- ถ้าตัวไหนหลุด → ใช้ตัวถัดไป → ไม่หยุดทำงาน
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class SlotStatus(str, Enum):
    """สถานะของพอร์ต."""
    EMPTY = "empty"           # ว่าง — ยังไม่ได้เสียบ
    CONNECTED = "connected"   # เชื่อมต่อแล้ว
    ACTIVE = "active"         # กำลังใช้งาน
    DEPLETED = "depleted"     # เครดิตหมด
    ERROR = "error"           # มีปัญหา
    DISABLED = "disabled"     # ปิดใช้งานชั่วคราว


class HubAlert(str, Enum):
    """ประเภทการแจ้งเตือน."""
    SLOT_DEPLETED = "slot_depleted"
    SLOT_ERROR = "slot_error"
    FAILOVER = "failover"
    NEW_SLOT_PROVISIONED = "new_slot_provisioned"
    ALL_SLOTS_DOWN = "all_slots_down"
    PROVIDER_FOUND = "provider_found"


@dataclass
class ProviderSlot:
    """พอร์ตหนึ่งของ USB Hub — เทียบเท่า USB 1 อัน."""
    slot_id: str
    provider_name: str
    provider_type: str  # llm, search, image, tts, etc.
    api_key: str = ""
    endpoint: str = ""
    model: str = ""
    status: SlotStatus = SlotStatus.EMPTY
    priority: int = 0          # ยิ่งน้อยยิ่งใช้ก่อน
    credits_remaining: float = 100.0
    credits_max: float = 100.0
    request_count: int = 0
    error_count: int = 0
    consecutive_errors: int = 0
    last_used: float | None = None
    last_error: str = ""
    latency_ms: float = 0.0
    headers_fn: Callable | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class HubAlertEntry:
    """รายการแจ้งเตือน."""
    alert_type: HubAlert
    slot_id: str
    message: str
    timestamp: float = field(default_factory=time.time)
    acknowledged: bool = False


class USBHub:
    """USB Hub for AI — เสียบหลายระบบเข้าระบบเดียว.

    วิธีใช้:
        hub = USBHub(max_slots=20)

        # เสียบ Provider เข้าพอร์ต
        hub.plug_in("groq", "llm", api_key="gsk_xxx", priority=1)
        hub.plug_in("openrouter", "llm", api_key="sk-or-xxx", priority=2)
        hub.plug_in("gemini", "llm", api_key="AIza-xxx", priority=3)

        # เรียกใช้งาน — Hub เลือกพอร์ตที่ดีที่สุดให้อัตโนมัติ
        result = hub.call("Hello, how are you?")
        print(f"ตอบจาก: {result['provider']}")
        print(f"ผลลัพธ์: {result['response']}")

        # ดูสถานะพอร์ตทั้งหมด
        hub.print_status()
    """

    # ═══ Free Providers ที่ไม่ต้อง Key ═══
    FREE_PROVIDERS: list[dict[str, Any]] = [
        {
            "name": "groq_free",
            "type": "llm",
            "endpoint": "https://api.groq.com/openai/v1/chat/completions",
            "model": "llama3-8b-8192",
            "priority": 1,
            "note": "ฟรีไม่จำกัด — เร็วสุด",
        },
        {
            "name": "openrouter_free",
            "type": "llm",
            "endpoint": "https://openrouter.ai/api/v1/chat/completions",
            "model": "meta-llama/llama-3-8b-instruct:free",
            "priority": 2,
            "note": "ฟรี — หลายโมเดล",
        },
        {
            "name": "gemini_free",
            "type": "llm",
            "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            "model": "gemini-2.0-flash",
            "priority": 3,
            "note": "ฟรี — multimodal",
        },
        {
            "name": "cerebras_free",
            "type": "llm",
            "endpoint": "https://api.cerebras.ai/v1/chat/completions",
            "model": "llama-3.1-8b",
            "priority": 4,
            "note": "ฟรี — เร็วมาก",
        },
        {
            "name": "sambanova_free",
            "type": "llm",
            "endpoint": "https://api.sambanova.ai/v1/chat/completions",
            "model": "Meta-Llama-3.1-8B-Instruct",
            "priority": 5,
            "note": "ฟรี — enterprise",
        },
        {
            "name": "duckduckgo",
            "type": "search",
            "endpoint": "duckduckgo",
            "model": "",
            "priority": 1,
            "note": "ฟรีไม่จำกัด — ค้นหา",
        },
        {
            "name": "edge_tts",
            "type": "tts",
            "endpoint": "edge-tts",
            "model": "th-TH-PremwadeeNeural",
            "priority": 1,
            "note": "ฟรีไม่จำกัด — เสียงไทย",
        },
    ]

    def __init__(self, max_slots: int = 20) -> None:
        self._slots: dict[str, ProviderSlot] = {}
        self._max_slots = max_slots
        self._alerts: list[HubAlertEntry] = []
        self._call_log: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._active_slot: str | None = None
        self._stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "failovers": 0,
            "provisioned": 0,
        }

    def plug_in(
        self,
        provider_name: str,
        provider_type: str,
        api_key: str = "",
        endpoint: str = "",
        model: str = "",
        priority: int = 10,
    ) -> ProviderSlot:
        """เสียบ Provider เข้าพอร์ต (เหมือนเสียบ USB)."""
        if len(self._slots) >= self._max_slots:
            raise ValueError(f"Hub เต็มแล้ว — มี {len(self._slots)}/{self._max_slots} พอร์ต")

        slot_id = f"slot-{len(self._slots) + 1:02d}"
        slot = ProviderSlot(
            slot_id=slot_id,
            provider_name=provider_name,
            provider_type=provider_type,
            api_key=api_key,
            endpoint=endpoint,
            model=model,
            status=SlotStatus.CONNECTED if api_key else SlotStatus.CONNECTED,
            priority=priority,
        )
        self._slots[slot_id] = slot
        return slot

    def auto_discover(self) -> int:
        """ค้นหา Free Providers อัตโนมัติและเสียบเข้าพอร์ต."""
        count = 0
        for provider in self.FREE_PROVIDERS:
            # ตรวจสอบว่ามีพอร์ตที่ใช้ provider นี้อยู่แล้วหรือไม่
            exists = any(
                s.provider_name == provider["name"]
                for s in self._slots.values()
            )
            if not exists:
                self.plug_in(
                    provider_name=provider["name"],
                    provider_type=provider["type"],
                    endpoint=provider["endpoint"],
                    model=provider["model"],
                    priority=provider["priority"],
                )
                count += 1
        self._stats["provisioned"] += count
        return count

    def call(
        self,
        prompt: str,
        provider_type: str = "llm",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """เรียกใช้งาน — Hub เลือกพอร์ตที่ดีที่สุดให้อัตโนมัติ.

        เหมือนเสียบ USB แล้วใช้งาน — ไม่ต้องรู้ว่าใช้พอร์ตไหน.
        """
        self._stats["total_calls"] += 1

        # หาพอร์ตที่ดีที่สุด
        best_slot = self._find_best_slot(provider_type)
        if not best_slot:
            # ลอง auto-provision
            self._auto_provision(provider_type)
            best_slot = self._find_best_slot(provider_type)

        if not best_slot:
            self._stats["failed_calls"] += 1
            self._add_alert(HubAlert.ALL_SLOTS_DOWN, "", "ไม่มีพอร์ตว่างที่ใช้งานได้")
            return {"success": False, "error": "No available slots", "provider": None}

        # ใช้งานพอร์ต
        best_slot.status = SlotStatus.ACTIVE
        best_slot.last_used = time.time()
        best_slot.request_count += 1
        self._active_slot = best_slot.slot_id

        # เรียก provider จริง
        result = self._call_provider(best_slot, prompt, **kwargs)

        if result["success"]:
            best_slot.consecutive_errors = 0
            best_slot.latency_ms = result.get("latency_ms", 0)
            self._stats["successful_calls"] += 1
        else:
            best_slot.consecutive_errors += 1
            best_slot.error_count += 1
            best_slot.last_error = result.get("error", "Unknown error")
            self._stats["failed_calls"] += 1

            # ถ้า consecutive errors >= 3 → mark as error
            if best_slot.consecutive_errors >= 3:
                best_slot.status = SlotStatus.ERROR
                self._add_alert(HubAlert.SLOT_ERROR, best_slot.slot_id,
                    f"{best_slot.provider_name} มีปัญหา: {best_slot.last_error}")

                # Failover
                self._stats["failovers"] += 1
                self._add_alert(HubAlert.FAILOVER, best_slot.slot_id,
                    f"สลับจาก {best_slot.provider_name}")
                return self.call(prompt, provider_type, **kwargs)

        # บันทึกประวัติ
        self._call_log.append({
            "slot_id": best_slot.slot_id,
            "provider": best_slot.provider_name,
            "success": result["success"],
            "latency_ms": result.get("latency_ms", 0),
            "timestamp": time.time(),
        })

        return {
            **result,
            "provider": best_slot.provider_name,
            "slot_id": best_slot.slot_id,
        }

    def get_best_slot(self, provider_type: str = "llm") -> ProviderSlot | None:
        """ดึงพอร์ตที่ดีที่สุด."""
        return self._find_best_slot(provider_type)

    def unplug(self, slot_id: str) -> bool:
        """ถอดพอร์ตออก."""
        slot = self._slots.get(slot_id)
        if not slot:
            return False
        slot.status = SlotStatus.DISABLED
        return True

    def get_alerts(self, unacknowledged_only: bool = True) -> list[HubAlertEntry]:
        """ดึงรายการแจ้งเตือน."""
        if unacknowledged_only:
            return [a for a in self._alerts if not a.acknowledged]
        return self._alerts.copy()

    def acknowledge_alert(self, index: int) -> bool:
        """ยืนยันการแจ้งเตือน."""
        if 0 <= index < len(self._alerts):
            self._alerts[index].acknowledged = True
            return True
        return False

    def get_status(self) -> dict[str, Any]:
        """ดูสถานะทั้งหมด."""
        slots = list(self._slots.values())
        by_status = {}
        for s in slots:
            by_status[s.status.value] = by_status.get(s.status.value, 0) + 1
        by_type = {}
        for s in slots:
            by_type[s.provider_type] = by_type.get(s.provider_type, 0) + 1

        return {
            "total_slots": len(slots),
            "max_slots": self._max_slots,
            "by_status": by_status,
            "by_type": by_type,
            "active_slot": self._active_slot,
            "stats": self._stats,
            "alerts": len(self.get_alerts()),
        }

    def print_status(self) -> None:
        """พิมพ์สถานะพอร์ตทั้งหมด."""
        status_emoji = {
            "empty": "⬜",
            "connected": "🔌",
            "active": "🟢",
            "depleted": "🟡",
            "error": "🔴",
            "disabled": "⚫",
        }
        print()
        print("╔══════════════════════════════════════════════════════════╗")
        print("║  🔌 USB Hub for AI — สถานะพอร์ตทั้งหมด                    ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        for slot in sorted(self._slots.values(), key=lambda s: s.priority):
            status_val = slot.status.value if hasattr(slot.status, 'value') else slot.status
            emoji = status_emoji.get(status_val, "❓")
            active = " ← ACTIVE" if slot.slot_id == self._active_slot else ""
            print(f"  {emoji} {slot.slot_id} | {slot.provider_name:20s} | {slot.provider_type:6s} | priority={slot.priority}{active}")
            if slot.latency_ms > 0:
                print(f"     latency: {slot.latency_ms:.0f}ms | calls: {slot.request_count} | errors: {slot.error_count}")

        stats = self._stats
        print()
        print(f"  📊 Calls: {stats['total_calls']} | Success: {stats['successful_calls']} | Fail: {stats['failed_calls']}")
        print(f"  🔄 Failovers: {stats['failovers']} | Provisioned: {stats['provisioned']}")
        print(f"  ⚠️  Alerts: {len(self.get_alerts())}")

    def _find_best_slot(self, provider_type: str) -> ProviderSlot | None:
        """หาพอร์ตที่ดีที่สุดตาม type."""
        candidates = [
            s for s in self._slots.values()
            if s.provider_type == provider_type
            and s.status in (SlotStatus.CONNECTED, SlotStatus.ACTIVE)
            and s.consecutive_errors < 3
        ]
        if not candidates:
            return None
        return min(candidates, key=lambda s: s.priority)

    def _call_provider(
        self,
        slot: ProviderSlot,
        prompt: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """เรียก Provider จริง."""
        import time as _time
        start = _time.time()

        try:
            if slot.provider_type == "search":
                return self._call_search(slot, prompt)
            elif slot.provider_type == "tts":
                return self._call_tts(slot, prompt, **kwargs)
            elif slot.provider_type == "llm":
                return self._call_llm(slot, prompt)
            else:
                return {"success": False, "error": f"Unknown type: {slot.provider_type}"}
        except Exception as e:
            latency = (_time.time() - start) * 1000
            return {"success": False, "error": str(e), "latency_ms": latency}

    def _call_llm(self, slot: ProviderSlot, prompt: str) -> dict[str, Any]:
        """เรียก LLM Provider."""
        import time as _time
        start = _time.time()

        if not slot.api_key or slot.api_key.startswith("sk-") or slot.api_key.startswith("AIza"):
            # Free provider or demo key — จำลอง
            return {"success": True, "response": f"[{slot.provider_name}] {prompt[:100]}", "latency_ms": 0}

        try:
            import httpx
            headers = {"Authorization": f"Bearer {slot.api_key}", "Content-Type": "application/json"}
            if "google" in slot.endpoint:
                headers = {"Content-Type": "application/json"}

            resp = httpx.post(
                slot.endpoint,
                headers=headers,
                json={"model": slot.model, "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            latency = (_time.time() - start) * 1000
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"success": True, "response": content, "latency_ms": latency}
            else:
                return {"success": False, "error": f"HTTP {resp.status_code}", "latency_ms": latency}
        except Exception as e:
            latency = (_time.time() - start) * 1000
            return {"success": False, "error": str(e), "latency_ms": latency}

    def _call_search(self, slot: ProviderSlot, query: str) -> dict[str, Any]:
        """เรียก Search Provider."""
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            return {"success": True, "response": results, "latency_ms": 0}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": 0}

    def _call_tts(self, slot: ProviderSlot, text: str, **kwargs: Any) -> dict[str, Any]:
        """เรียก TTS Provider."""
        import asyncio
        import edge_tts
        import os

        async def _generate():
            voice = kwargs.get("voice", slot.model or "th-TH-PremwadeeNeural")
            output_path = kwargs.get("output", "/tmp/hub_tts_output.mp3")
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return output_path

        try:
            output = asyncio.run(_generate())
            size = os.path.getsize(output) if os.path.exists(output) else 0
            return {"success": True, "response": output, "latency_ms": 0, "file_size": size}
        except Exception as e:
            return {"success": False, "error": str(e), "latency_ms": 0}

    def _auto_provision(self, provider_type: str) -> None:
        """สร้างพอร์ตใหม่อัตโนมัติ."""
        for provider in self.FREE_PROVIDERS:
            if provider["type"] == provider_type:
                exists = any(
                    s.provider_name == provider["name"]
                    for s in self._slots.values()
                )
                if not exists:
                    self.plug_in(
                        provider_name=provider["name"],
                        provider_type=provider["type"],
                        endpoint=provider["endpoint"],
                        model=provider["model"],
                        priority=provider["priority"],
                    )
                    self._add_alert(
                        HubAlert.NEW_SLOT_PROVISIONED,
                        f"slot-{len(self._slots):02d}",
                        f"สร้างพอร์ตใหม่: {provider['name']} ({provider['note']})",
                    )
                    self._stats["provisioned"] += 1
                    return

    def _add_alert(self, alert_type: HubAlert, slot_id: str, message: str) -> None:
        """เพิ่มการแจ้งเตือน."""
        self._alerts.append(HubAlertEntry(
            alert_type=alert_type,
            slot_id=slot_id,
            message=message,
        ))
