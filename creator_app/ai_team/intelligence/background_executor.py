"""Background Executor — ทำงานเบื้องหลังอัตโนมัติ.

ให้ Agent สามารถ:
1. รับงาน → บันทึก → ทำในเบื้องหลัง → แจ้งผลเมื่อเสร็จ
2. จัดตารางงานล่วงหน้า (schedule)
3. Fire-and-forget — ตั้งไว้แล้วไม่ต้องคุม
4. จัดการหน่วยความจำของงานที่กำลังทำ

อ้างอิง:
- koboi-agent (background memory + scheduling)
- docketeer (future task scheduling)
- cueclaw (natural language → DAG)
- agent-orchestrator (multi-agent scheduling)
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskStatus(str, Enum):
    """สถานะของงาน."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


class TaskPriority(str, Enum):
    """ลำดับความสำคัญ."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class BackgroundTask:
    """งานที่ทำในเบื้องหลัง."""
    task_id: str
    name: str
    description: str
    handler: str  # ชื่อฟังก์ชัน/handler ที่จะเรียก
    args: tuple = ()
    kwargs: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.QUEUED
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    result: Any = None
    error: str = ""
    retries: int = 0
    max_retries: int = 3
    timeout: float = 300.0  # วินาที
    scheduled_at: float | None = None  # สำหรับ scheduled tasks
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """ผลลัพธ์ของงาน."""
    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    duration: float = 0.0
    completed_at: float = field(default_factory=time.time)


class BackgroundExecutor:
    """ตัวทำงานเบื้องหลัง — Fire and Forget.

    วิธีใช้:
        executor = BackgroundExecutor()

        # สั่งงาน
        task = executor.submit(
            name="sync_gmail",
            handler="gmail_sync",
            args=("spinlnw10@gmail.com",),
            priority=TaskPriority.HIGH,
        )

        # สั่งงานแบบ scheduled
        task = executor.schedule(
            name="daily_report",
            handler="generate_report",
            cron="0 9 * * *",  # ทุกวัน 9 โมง
        )

        # ดูสถานะ
        status = executor.get_status()
        # {'total': 5, 'running': 1, 'completed': 3, 'queued': 1}
    """

    def __init__(self, max_workers: int = 4) -> None:
        self._tasks: dict[str, BackgroundTask] = {}
        self._results: dict[str, TaskResult] = {}
        self._handlers: dict[str, Callable] = {}
        self._max_workers = max_workers
        self._running = 0
        self._lock = threading.Lock()
        self._task_counter = 0

    def register_handler(self, name: str, handler: Callable) -> None:
        """ลงทะเบียน handler สำหรับงาน."""
        self._handlers[name] = handler

    def submit(
        self,
        name: str,
        handler: str,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: float = 300.0,
        tags: list[str] | None = None,
    ) -> BackgroundTask:
        """สั่งงานให้ทำในเบื้องหลัง."""
        self._task_counter += 1
        task_id = f"task-{self._task_counter:06d}"

        task = BackgroundTask(
            task_id=task_id,
            name=name,
            description=f"Background task: {name}",
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            timeout=timeout,
            tags=tags or [],
        )

        self._tasks[task_id] = task

        # ถ้ามี handler ที่ลงทะเบียนไว้ → เริ่มทำงานทันที
        if handler in self._handlers:
            self._start_task(task)

        return task

    def schedule(
        self,
        name: str,
        handler: str,
        cron: str | None = None,
        delay_seconds: float | None = None,
        args: tuple = (),
        kwargs: dict[str, Any] | None = None,
    ) -> BackgroundTask:
        """จัดตารางงานล่วงหน้า."""
        self._task_counter += 1
        task_id = f"task-{self._task_counter:06d}"

        scheduled_at = time.time()
        if delay_seconds:
            scheduled_at += delay_seconds

        task = BackgroundTask(
            task_id=task_id,
            name=name,
            description=f"Scheduled task: {name} (cron={cron})",
            handler=handler,
            args=args,
            kwargs=kwargs or {},
            scheduled_at=scheduled_at,
            tags=["scheduled"],
            metadata={"cron": cron},
        )

        self._tasks[task_id] = task
        return task

    def cancel(self, task_id: str) -> bool:
        """ยกเลิกงาน."""
        task = self._tasks.get(task_id)
        if not task:
            return False
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False
        task.status = TaskStatus.CANCELLED
        return True

    def get_task(self, task_id: str) -> BackgroundTask | None:
        """ดึงข้อมูลงาน."""
        return self._tasks.get(task_id)

    def get_status(self) -> dict[str, Any]:
        """ดูสถานะทั้งหมด."""
        counts: dict[str, int] = {}
        for task in self._tasks.values():
            status = task.status.value
            counts[status] = counts.get(status, 0) + 1

        return {
            "total": len(self._tasks),
            "by_status": counts,
            "running": self._running,
            "max_workers": self._max_workers,
            "handlers_registered": list(self._handlers.keys()),
        }

    def list_tasks(
        self,
        status: TaskStatus | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[BackgroundTask]:
        """ listar งานตามเงื่อนไข."""
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]
        if tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in tags)]

        # เรียงตาม priority + created_at
        priority_order = {
            TaskPriority.URGENT: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 9), t.created_at))

        return tasks[:limit]

    def get_results(self, task_id: str) -> TaskResult | None:
        """ดึงผลลัพธ์ของงาน."""
        return self._results.get(task_id)

    def _start_task(self, task: BackgroundTask) -> None:
        """เริ่มทำงาน (ใน thread แยก)."""
        with self._lock:
            if self._running >= self._max_workers:
                return  # รอคิว
            self._running += 1

        task.status = TaskStatus.RUNNING
        task.started_at = time.time()

        thread = threading.Thread(
            target=self._run_task,
            args=(task,),
            daemon=True,
        )
        thread.start()

    def _run_task(self, task: BackgroundTask) -> None:
        """รันงานจริง."""
        try:
            handler = self._handlers.get(task.handler)
            if not handler:
                raise ValueError(f"Handler '{task.handler}' not found")

            result = handler(*task.args, **task.kwargs)

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = time.time()

            self._results[task.task_id] = TaskResult(
                task_id=task.task_id,
                success=True,
                result=result,
                duration=task.completed_at - (task.started_at or task.created_at),
            )

        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.completed_at = time.time()

            # Retry ถ้ายังไม่เกิน max
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.QUEUED
                self._start_task(task)
                return

            self._results[task.task_id] = TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(exc),
                duration=task.completed_at - (task.started_at or task.created_at),
            )

        finally:
            with self._lock:
                self._running -= 1

    def summary(self) -> str:
        """สรุปสถานะแบบ text."""
        status = self.get_status()
        lines = [
            "╔══════════════════════════════════════════════════╗",
            "║  ⚙️ Background Executor — สถานะ                  ║",
            "╚══════════════════════════════════════════════════╝",
            "",
            f"📊 งานทั้งหมด: {status['total']}",
            f"🔄 กำลังทำ: {status['running']}/{status['max_workers']}",
        ]
        for s, count in status["by_status"].items():
            emoji = {
                "queued": "⏳",
                "running": "🔄",
                "completed": "✅",
                "failed": "❌",
                "cancelled": "🚫",
            }.get(s, "❓")
            lines.append(f"   {emoji} {s}: {count}")

        if status["handlers_registered"]:
            lines.append(f"\n🔧 Handlers: {', '.join(status['handlers_registered'])}")

        return "\n".join(lines)
