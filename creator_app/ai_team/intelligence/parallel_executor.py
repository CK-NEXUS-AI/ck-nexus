"""Parallel Executor — รันหลายงานพร้อมกัน.

รัน task แบบขนานด้วย asyncio — เร็วขึ้น 2-5 เท่า
มี fallback อัตโนมัติเมื่อ task ล้มเหลว
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from creator_app.ai_team.cancellation import CancellationRequested


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """ผลลัพธ์ของ task หนึ่งตัว."""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: str | None = None
    duration_sec: float = 0.0
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class ParallelBatch:
    """ชุดงานที่รันพร้อมกัน."""

    batch_id: str
    tasks: list[TaskResult] = field(default_factory=list)
    max_concurrency: int = 5


class ParallelExecutor:
    """รันหลายงานพร้อมกัน — เร็วขึ้น 2-5 เท่า.

    วิธีใช้:
        executor = ParallelExecutor()
        tasks = [
            ("scan-email", lambda: scan_inbox()),
            ("check-calendar", lambda: check_calendar()),
            ("generate-report", lambda: generate_report()),
        ]
        results = await executor.run_batch("morning-check", tasks)
        for r in results:
            print(f"{r.task_id}: {r.status.value} ({r.duration_sec:.1f}s)")
    """

    def __init__(self, *, max_concurrency: int = 5):
        self._max_concurrency = max_concurrency
        self._history: list[ParallelBatch] = []
        self._semaphore: asyncio.Semaphore | None = None

    async def run_batch(
        self,
        batch_id: str,
        tasks: list[tuple[str, Callable[[], Awaitable[Any]] | Callable[[], Any]]],
        *,
        timeout: float = 30.0,
        fallback: Callable[[str, Exception], Any] | None = None,
    ) -> list[TaskResult]:
        """รันชุดงานพร้อมกัน — จำกัด concurrency ด้วย semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrency)

        results: list[TaskResult] = []
        coros: list[Coroutine] = []

        for task_id, func in tasks:
            coros.append(self._run_single(task_id, func, timeout, fallback))

        results = list(await asyncio.gather(*coros, return_exceptions=False))
        batch = ParallelBatch(
            batch_id=batch_id, tasks=results, max_concurrency=self._max_concurrency
        )
        self._history.append(batch)
        return results

    async def _run_single(
        self,
        task_id: str,
        func: Callable[[], Awaitable[Any]] | Callable[[], Any],
        timeout: float,
        fallback: Callable[[str, Exception], Any] | None,
    ) -> TaskResult:
        """รัน task เดียว — พร้อม timeout และ error handling."""
        result = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
        start = time.time()

        async with self._semaphore:  # type: ignore[misc]
            try:
                start = time.time()
                result.status = TaskStatus.RUNNING
                result.started_at = start

                if asyncio.iscoroutinefunction(func):
                    value = await asyncio.wait_for(func(), timeout=timeout)
                else:
                    loop = asyncio.get_event_loop()
                    value = await asyncio.wait_for(
                        loop.run_in_executor(None, func), timeout=timeout
                    )

                result.status = TaskStatus.COMPLETED
                result.result = value
            except CancellationRequested as exc:
                result.status = TaskStatus.CANCELLED
                result.error = str(exc)
            except TimeoutError:
                result.status = TaskStatus.FAILED
                result.error = f"Timeout after {timeout}s"
                if fallback:
                    try:
                        result.result = fallback(task_id, TimeoutError(result.error))
                        result.status = TaskStatus.COMPLETED
                        result.error = None
                    except Exception as exc:
                        result.error = f"Fallback also failed: {exc}"
            except Exception as exc:
                result.status = TaskStatus.FAILED
                result.error = str(exc)
                if fallback:
                    try:
                        result.result = fallback(task_id, exc)
                        result.status = TaskStatus.COMPLETED
                        result.error = None
                    except Exception as fb_exc:
                        result.error = f"Fallback also failed: {fb_exc}"
            finally:
                result.completed_at = time.time()
                result.duration_sec = result.completed_at - result.started_at

        return result

    async def run_sequential(
        self,
        tasks: list[tuple[str, Callable[[], Awaitable[Any]] | Callable[[], Any]]],
    ) -> list[TaskResult]:
        """รันทีละตัว — สำหรับงานที่มีลำดับ."""
        results: list[TaskResult] = []
        for task_id, func in tasks:
            r = TaskResult(task_id=task_id, status=TaskStatus.PENDING)
            start = time.time()
            r.started_at = start
            r.status = TaskStatus.RUNNING
            try:
                if asyncio.iscoroutinefunction(func):
                    r.result = await func()
                else:
                    r.result = func()
                r.status = TaskStatus.COMPLETED
            except Exception as exc:
                r.status = TaskStatus.FAILED
                r.error = str(exc)
            finally:
                r.completed_at = time.time()
                r.duration_sec = r.completed_at - r.started_at
                results.append(r)
        return results

    @property
    def history(self) -> list[ParallelBatch]:
        return list(self._history)

    def stats(self) -> dict[str, Any]:
        total_tasks = sum(len(b.tasks) for b in self._history)
        completed = sum(
            1 for b in self._history for t in b.tasks if t.status == TaskStatus.COMPLETED
        )
        failed = sum(1 for b in self._history for t in b.tasks if t.status == TaskStatus.FAILED)
        return {
            "total_batches": len(self._history),
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "success_rate_percent": round((completed / total_tasks * 100) if total_tasks else 0, 1),
        }
