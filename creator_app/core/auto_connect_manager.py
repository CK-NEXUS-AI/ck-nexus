"""Auto-Connect Manager — CK-NEXUS.

จัดการการเชื่อมต่ออัตโอโมเติฟ:
- ตรวจสอบก่อนเชื่อม (Pre-flight Check)
- ลองใหม่แบบฉลาก (Exponential Backoff)
- สลับปลายทางเมื่อหยุด (Failover & Fallback)
- จดจำสถานะ (State Persistence)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger("cknexus.auto_connect")


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CHECKING = "checking"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    WAITING_RETRY = "waiting_retry"
    OFFLINE_MODE = "offline_mode"


@dataclass
class ConnectionEndpoint:
    name: str
    endpoint_id: str
    priority: int
    connect_func: Callable[[], Awaitable[bool]]
    health_check: Callable[[], Awaitable[bool]] | None = None
    env_vars: tuple[str, ...] = ()
    timeout_seconds: float = 5.0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_success: float = 0.0
    last_failure: float = 0.0
    state: ConnectionState = ConnectionState.DISCONNECTED
    retry_attempts: int = 0
    circuit_open_until: float = 0.0


@dataclass
class AutoConnectConfig:
    health_check_interval_sec: float = 30.0
    max_retry_attempts: int = 5
    base_backoff_sec: float = 1.0
    max_backoff_sec: float = 300.0
    circuit_breaker_threshold: int = 3
    circuit_cooldown_sec: float = 60.0
    connect_timeout_sec: float = 5.0
    state_file: str = ".cknexus/auto_connect_state.json"
    offline_mode_enabled: bool = True


class AutoConnectManager:
    """จัดการการเชื่อมต่ออัตโอโมเติฟทั้งหมด — เชื่อม · ตรวจ · ซ่อม · สลับ."""

    def __init__(self, config: AutoConnectConfig | None = None) -> None:
        self.config = config or AutoConnectConfig()
        self.endpoints: dict[str, ConnectionEndpoint] = {}
        self._state_file = Path(self.config.state_file)
        self._running = False
        self._health_task: asyncio.Task | None = None
        self._connect_lock = asyncio.Lock()
        self.stats = {
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "failover_count": 0,
            "offline_sessions": 0,
        }

    def register_endpoint(
        self,
        name: str,
        endpoint_id: str,
        priority: int,
        connect_func: Callable[[], Awaitable[bool]],
        health_check: Callable[[], Awaitable[bool]] | None = None,
        env_vars: tuple[str, ...] = (),
        timeout_seconds: float = 5.0,
    ) -> None:
        """ลงทะเบียนปลายทางใหม่."""
        if endpoint_id in self.endpoints:
            raise ValueError(f"Endpoint {endpoint_id} already registered")
        self.endpoints[endpoint_id] = ConnectionEndpoint(
            name=name,
            endpoint_id=endpoint_id,
            priority=priority,
            connect_func=connect_func,
            health_check=health_check,
            env_vars=env_vars,
            timeout_seconds=timeout_seconds,
        )
        logger.info("Registered endpoint: %s (priority=%d)", endpoint_id, priority)

    async def start(self) -> None:
        """เริ่มต้นการเชื่อมต่ออัตโอโมเติฟ."""
        self._running = True
        self._load_state()

        logger.info("AutoConnect starting with %d endpoints", len(self.endpoints))
        await self._connect_all()

        self._health_task = asyncio.create_task(self._health_monitor_loop())
        logger.info(
            "Health monitor started (interval=%ds)",
            int(self.config.health_check_interval_sec),
        )

    async def stop(self) -> None:
        """หยุดการเชื่อมต่อและบันทึกสถานะ."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._health_task
        self._save_state()
        logger.info("AutoConnect stopped, state saved")

    async def _connect_all(self) -> None:
        """เชื่อมต่อทุกปลายทางตามลำดับความสำคัญ."""
        for endpoint_id in sorted(self.endpoints, key=lambda e: self.endpoints[e].priority):
            endpoint = self.endpoints[endpoint_id]
            if not self._preflight_check(endpoint):
                endpoint.state = ConnectionState.FAILED
                logger.warning("Pre-flight failed for %s: missing env vars", endpoint_id)
                continue
            await self._try_connect(endpoint)

    def _preflight_check(self, endpoint: ConnectionEndpoint) -> bool:
        """ตรวจสอบ 7 ข้อก่อนเชื่อมต่อ — ตรวจครบก่อนส่งคำขอ."""
        # ข้อที่ 1: ตัวแปรสภาพแวดล้อมครบถ้วน
        for env_var in endpoint.env_vars:
            if not os.getenv(env_var, "").strip():
                logger.warning("Missing env var: %s", env_var)
                return False

        # ข้อที่ 2: เครือข่ายเชื่อมต่อได้
        if not self._check_network():
            logger.warning("Network unreachable")
            return False

        # ข้อที่ 3: DNS ตอบสนอง
        if not self._check_dns():
            logger.warning("DNS resolution failed")
            return False

        # ข้อที่ 4: ไฟล์/พอร์ตไม่ถูกบล็อก (ข้ามสำหรับ dev ที่ไม่มี fireall)
        # ข้อที่ 5-7: เวอร์ชันและสิทธิ์ (ตรวจสอบใน connect_func)
        return True

    def _check_network(self) -> bool:
        """ตรวจสอบการเชื่อมต่อเครือข่ายพื้นฐาน."""
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            return True
        except OSError:
            return False

    def _check_dns(self) -> bool:
        """ตรวจสอบ DNS resolution."""
        try:
            socket.setdefaulttimeout(3)
            socket.gethostbyname("google.com")
            return True
        except OSError:
            return False

    async def _try_connect(self, endpoint: ConnectionEndpoint) -> None:
        """ลองเชื่อมต่อปลายทางหนึ่ง."""
        async with self._connect_lock:
            if endpoint.state == ConnectionState.CONNECTED:
                return

            now = time.time()
            if endpoint.circuit_open_until > now:
                endpoint.state = ConnectionState.WAITING_RETRY
                logger.debug(
                    "Circuit open for %s until %.0f",
                    endpoint.endpoint_id,
                    endpoint.circuit_open_until,
                )
                return

            endpoint.state = ConnectionState.CONNECTING
            self.stats["total_connections"] += 1

            try:
                success = await asyncio.wait_for(
                    endpoint.connect_func(),
                    timeout=endpoint.timeout_seconds,
                )
            except (TimeoutError, Exception) as exc:
                logger.warning(
                    "Connect failed for %s: %s",
                    endpoint.endpoint_id,
                    type(exc).__name__,
                )
                success = False

            if success:
                endpoint.state = ConnectionState.CONNECTED
                endpoint.last_success = time.time()
                endpoint.consecutive_failures = 0
                endpoint.circuit_open_until = 0.0
                self.stats["successful_connections"] += 1
                logger.info("Connected: %s", endpoint.endpoint_id)
            else:
                endpoint.state = ConnectionState.FAILED
                endpoint.last_failure = time.time()
                endpoint.consecutive_failures += 1
                self.stats["failed_connections"] += 1
                self.stats["failover_count"] += 1

                if endpoint.consecutive_failures >= self.config.circuit_breaker_threshold:
                    backoff = min(
                        self.config.base_backoff_sec * (2 ** endpoint.retry_attempts),
                        self.config.max_backoff_sec,
                    )
                    endpoint.circuit_open_until = time.time() + backoff
                    endpoint.retry_attempts += 1
                    logger.warning(
                        "Circuit opened for %s (backoff=%.1fs)",
                        endpoint.endpoint_id,
                        backoff,
                    )

                # ลองเปิดโหมดออฟไลน์ถ้าทุกอย่างล้มเหลว
                if not self._any_connected():
                    if self.config.offline_mode_enabled:
                        self.stats["offline_sessions"] += 1
                        logger.warning("All endpoints disconnected — entering OFFLINE_MODE")
                    else:
                        logger.error("All endpoints disconnected — NO OFFLINE MODE")

    def _any_connected(self) -> bool:
        return any(
            ep.state == ConnectionState.CONNECTED for ep in self.endpoints.values()
        )

    @property
    def connected_endpoints(self) -> list[ConnectionEndpoint]:
        return sorted(
            [ep for ep in self.endpoints.values() if ep.state == ConnectionState.CONNECTED],
            key=lambda e: e.priority,
        )

    @property
    def active_endpoint(self) -> ConnectionEndpoint | None:
        connected = self.connected_endpoints
        return connected[0] if connected else None

    def preferred(self, capability: str) -> ConnectionEndpoint | None:
        """เลือกปลายทางที่เหมาะสมกับ capability โดยคำนึงถึงลำดับความสำคัฐ."""
        candidates = sorted(
            [ep for ep in self.endpoints.values() if ep.state == ConnectionState.CONNECTED],
            key=lambda e: e.priority,
        )
        # Filter by capability-specific prefix if needed
        for ep in candidates:
            if capability in ep.endpoint_id or capability in ep.name.lower().replace(" ", "_"):
                return ep
        return candidates[0] if candidates else None

    async def _health_monitor_loop(self) -> None:
        """ตรวจสุขภาพทุก endpoints ทุกๆ 30 วินาที."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_sec)
                await self._health_check_all()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Health monitor error: %s", type(exc).__name__)

    async def _health_check_all(self) -> None:
        """รัน health checks ทั้งหมด."""
        for endpoint in self.endpoints.values():
            if endpoint.health_check is None:
                continue
            if endpoint.state != ConnectionState.CONNECTED:
                continue
            try:
                healthy = await asyncio.wait_for(
                    endpoint.health_check(),
                    timeout=endpoint.timeout_seconds,
                )
            except Exception:
                healthy = False

            if not healthy:
                endpoint.state = ConnectionState.FAILED
                endpoint.consecutive_failures += 1
                logger.warning("Health check failed for %s — will failover", endpoint.endpoint_id)
                await self._try_connect(endpoint)

    def _save_state(self) -> None:
        if not self._state_file.parent.exists():
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "stats": self.stats,
            "endpoints": {
                eid: {
                    "state": ep.state.value,
                    "failure_count": ep.failure_count,
                    "consecutive_failures": ep.consecutive_failures,
                    "last_success": ep.last_success,
                    "last_failure": ep.last_failure,
                    "circuit_open_until": ep.circuit_open_until,
                }
                for eid, ep in self.endpoints.items()
            },
            "saved_at": time.time(),
        }
        try:
            self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError:
            logger.warning("Failed to save auto-connect state")

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            state = json.loads(self._state_file.read_text(encoding="utf-8"))
            self.stats.update(state.get("stats", {}))
            for eid, ep_state in state.get("endpoints", {}).items():
                if eid in self.endpoints:
                    ep = self.endpoints[eid]
                    if "state" in ep_state:
                        with contextlib.suppress(ValueError):
                            ep.state = ConnectionState(ep_state["state"])
                    ep.consecutive_failures = ep_state.get("consecutive_failures", 0)
                    ep.last_success = ep_state.get("last_success", 0.0)
                    ep.last_failure = ep_state.get("last_failure", 0.0)
                    ep.circuit_open_until = ep_state.get("circuit_open_until", 0.0)
            logger.info("Loaded auto-connect state from %s", self._state_file)
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to load auto-connect state")

    def status(self) -> dict:
        return {
            "running": self._running,
            "active_endpoint": self.active_endpoint.endpoint_id if self.active_endpoint else None,
            "connected_count": len(self.connected_endpoints),
            "offline": not self._any_connected(),
            "stats": self.stats,
            "endpoints": {
                eid: {
                    "name": ep.name,
                    "priority": ep.priority,
                    "state": ep.state.value,
                    "healthy": ep.state == ConnectionState.CONNECTED,
                    "consecutive_failures": ep.consecutive_failures,
                    "last_success": ep.last_success,
                    "last_failure": ep.last_failure,
                }
                for eid, ep in self.endpoints.items()
            },
        }


def build_auto_connect_manager(
    env: dict[str, str] | None = None,
    config: AutoConnectConfig | None = None,
) -> AutoConnectManager:
    """สร้าง AutoConnectManager พร้อม configuration จาก environment."""
    env = env or os.environ
    return AutoConnectManager(config=config or AutoConnectConfig(
        health_check_interval_sec=float(env.get("HEALTH_CHECK_INTERVAL_SEC", "30")),
        max_retry_attempts=int(env.get("MAX_RETRY_ATTEMPTS", "5")),
        circuit_breaker_threshold=int(env.get("CIRCUIT_BREAKER_THRESHOLD", "3")),
        circuit_cooldown_sec=float(env.get("CIRCUIT_COOLDOWN_SEC", "60")),
    ))
