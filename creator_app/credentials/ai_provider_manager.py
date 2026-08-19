"""AI Provider Manager — จัดการการเชื่อมต่อ AI หลายเจ้าอย่างอัตโอโมเติฟ.

รวมเข้ากับ:
- LlmKeyPool (การสลับ/หมุนเวียนคีย์อัตโอโมเติฟเมื่อใกล้หมดเครดิต)
- CredentialBroker (การจัดการ credential แบบ least-privilege)
- CapabilityRegistry (ฐานข้อมูล capabilities)
- AutoConnectManager (การเชื่อมต่อ/ซ่อม/สลับอัตโอโมเติฟ)

วิธีใช้:
python
from creator_app.credentials import AiProviderManager

mgr = AiProviderManager.from_environment()
await mgr.start()

provider = mgr.select_provider("openai.responses")
if provider:
    key, base_url, model = provider
    # ใช้ key เพื่อเรียก API — key ถูกจัดการอัตโอโมเติฟโดยระบบ

```
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from creator_app.core.auto_connect_manager import (
    AutoConnectConfig,
    AutoConnectManager,
)
from creator_app.credentials.capability_registry import (
    Capability,
    CapabilityRegistry,
)
from creator_app.credentials.credential_broker import (
    CredentialBroker,
    CredentialUnavailable,
)
from creator_app.credentials.llm_keypool import (
    LlmKeyPool,
    LlmKeySelection,
    LlmKeyStatus,
)

logger = logging.getLogger("cknexus.ai_provider")


@dataclass(frozen=True, slots=True)
class ResolvedProvider:
    """ผลลัพธ์การเลือก provider — ไม่มี secret ในนี้."""

    provider: str
    key_id: str
    base_url: str
    model: str
    source: str
    quota_pct_used: float | None
    health: str
    latency_ms: int
    priority: int


class AiProviderManager:
    """ผู้จัดการ AI Provider ระดับสูง — รวมทุกระบบเข้าด้วยกัน."""

    DEFAULT_PRIORITY = {
        "groq": 1,
        "openrouter": 2,
        "openai": 3,
        "anthropic": 4,
        "deepseek": 5,
    }

    def __init__(
        self,
        broker: CredentialBroker,
        keypool: LlmKeyPool | None = None,
        registry: CapabilityRegistry | None = None,
        auto_connect: AutoConnectManager | None = None,
    ) -> None:
        self.broker = broker
        self.keypool = keypool
        self.registry = registry or CapabilityRegistry()
        self.auto_connect = auto_connect
        self._started = False

    @classmethod
    def from_environment(cls) -> AiProviderManager:
        """สร้างจาก environment variables."""
        broker = CredentialBroker.from_environment()
        keypool = LlmKeyPool.from_environment()
        registry = CapabilityRegistry()

        config = AutoConnectConfig(
            health_check_interval_sec=float(os.getenv("HEALTH_CHECK_INTERVAL_SEC", "30")),
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "5")),
            circuit_breaker_threshold=int(os.getenv("CIRCUIT_BREAKER_THRESHOLD", "3")),
        )

        return cls(
            broker=broker,
            keypool=keypool,
            registry=registry,
            auto_connect=AutoConnectManager(config=config),
        )

    async def start(self) -> None:
        """เริ่มต้นระบบทั้งหมด."""
        self._started = True
        logger.info("AiProviderManager started")

        # Register AI provider endpoints with auto-connect
        if self.auto_connect and self.keypool:
            for spec in self.keypool.specs:
                self._register_provider_endpoint(spec)

            await self.auto_connect.start()  # noqa: E501

    async def stop(self) -> None:
        """หยุดระบบทั้งหมด."""
        if self.auto_connect:
            await self.auto_connect.stop()
        self._started = False
        logger.info("AiProviderManager stopped")

    def _register_provider_endpoint(self, spec) -> None:
        """ลงทะเบียน provider เข้ากับ auto-connect."""
        if not self.auto_connect:
            return

        priority = self.DEFAULT_PRIORITY.get(spec.id, 99)

        async def connect_func() -> bool:
            return os.getenv(spec.env_var, "").strip()

        async def health_check() -> bool:
            if self.keypool:
                statuses = self.keypool.status()
                key_status = next((s for s in statuses if s.key_id == spec.id), None)
                if key_status and key_status.healthy:
                    return True
            return False

        self.auto_connect.register_endpoint(
            name=f"LLM {spec.id}",
            endpoint_id=f"llm_{spec.id}",
            priority=priority,
            connect_func=connect_func,
            health_check=health_check,
            env_vars=(spec.env_var,),
            timeout_seconds=5.0,
        )

    def select_provider(self, capability: str) -> ResolvedProvider | None:
        """เลือก provider ที่ดีที่สุดสำหรับ capability ที่ระบุ.

        ใช้ scoring:
        capability, scope, health, quota, rate limit, cost, latency, region, expiry, policy risk
        """
        spec = self.registry.get(capability)
        if spec is None:
            logger.warning("Unknown capability: %s", capability)
            return None

        # ใช้ keypool เพื่อเลือก key สำหร้บ openai.responses
        if self.keypool and capability == Capability.OPENAI_RESPONSES.value:
            selection = self.keypool.acquire()
            if selection:
                statuses = self.keypool.status()
                key_status = next((s for s in statuses if s.key_id == selection.key_id), None)
                return ResolvedProvider(
                    provider=selection.provider,
                    key_id=selection.key_id,
                    base_url=selection.base_url,
                    model=selection.model,
                    source=selection.source if hasattr(selection, "source") else "keypool",
                    quota_pct_used=key_status.quota_percentage_used() if key_status else None,
                    health="healthy" if key_status and key_status.healthy else "unknown",
                    latency_ms=0,
                    priority=5,
                )
            return None

        return None

    def status(self) -> dict:
        """สถานะรวมของทุกระบบ."""
        result: dict = {
            "started": self._started,
        }

        if self.keypool:
            statuses = self.keypool.status()
            result["providers"] = [
                {
                    "id": s.key_id,
                    "provider": s.provider,
                    "model": s.model,
                    "free": s.free,
                    "healthy": s.healthy,
                    "exhausted": s.exhausted,
                    "cooldown_until": s.cooldown_until,
                    "quota_pct": s.quota_percentage_used,
                    "source": s.source,
                }
                for s in statuses
            ]
            result["free_fallback"] = self.keypool.free_fallback

        if self.auto_connect:
            result["connections"] = self.auto_connect.status()

        result["broker"] = {
            "configured_credentials": len(
                [s for s in self.broker.statuses(consumer="*") if s.configured]
            ),
        }

        return result

    @property
    def all_providers(self) -> list[LlmKeyStatus]:
        """รายชื่อ provider ทั้งหมดที่กำลังใช้งาน."""
        if self.keypool:
            return list(self.keypool.status())
        return []

    def get_best_key(self) -> LlmKeySelection | None:
        """ดึง key ที่ดีที่สุดจาก pool (อัตโอโมเติฟหากต้องการสลับ)."""
        if not self.keypool:
            return None
        return self.keypool.acquire()

    async def route(
        self, prompt: str, capability: str = "openai.responses"
    ) -> tuple[str, str, str]:
        """เส้นทางลัด: เลือก provider และคืนค่า (api_key, base_url, model).

        ใช้โดย caller ที่ต้องการเรียก API โดยตรง.
        """
        provider = self.select_provider(capability)
        if provider is None:
            if self.keypool:
                selection = self.keypool.acquire()
                if selection:
                    return (selection.api_key, selection.base_url, selection.model)
            raise CredentialUnavailable("No available AI provider for this request")

        if self.keypool:
            selection = self.keypool.acquire()
            if selection:
                return (selection.api_key, selection.base_url, selection.model)

        raise CredentialUnavailable("No available AI provider for this request")


def build_ai_provider_manager(env: dict[str, str] | None = None) -> AiProviderManager:
    """Factory สำหรับสร้างจาก environment."""
    env = env or os.environ
    broker = CredentialBroker.from_environment()
    keypool = LlmKeyPool.from_environment()
    return AiProviderManager(broker=broker, keypool=keypool)
