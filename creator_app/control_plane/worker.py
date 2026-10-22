"""Bounded, sandbox-only queue worker for control-plane tasks."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any, Protocol

from .task_store import TaskStore
from .verification import ControlPlaneVerifier


class TaskHandler(Protocol):
    def __call__(self, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class WorkerResult:
    state: str
    release_evidence: bool = False
    production_status: str = "NO-GO"
    external_mutation_authorized: bool = False
    attempts: int = 0
    error: str | None = None
    evidence_refs: tuple[str, ...] = ()


class RepairWorker:
    """Claim one task, execute an injected handler, verify, and finish safely."""

    def __init__(
        self,
        *,
        store: TaskStore,
        verifier: ControlPlaneVerifier,
        handlers: Mapping[str, TaskHandler],
        worker_id: str,
        execution_timeout: float = 300,
        lease_seconds: float | None = None,
    ) -> None:
        if not worker_id.strip():
            raise ValueError("worker_id must not be empty")
        if execution_timeout <= 0:
            raise ValueError("execution_timeout must be positive")
        self.store = store
        self.verifier = verifier
        self.handlers = handlers
        self.worker_id = worker_id
        self.execution_timeout = execution_timeout
        self.lease_seconds = (
            lease_seconds if lease_seconds is not None else max(300.0, execution_timeout)
        )

    def _result(
        self,
        state: str,
        *,
        attempts: int = 0,
        error: str | None = None,
        evidence_refs: tuple[str, ...] = (),
        release_evidence: bool = False,
    ) -> WorkerResult:
        return WorkerResult(
            state=state,
            release_evidence=release_evidence,
            production_status="NO-GO",
            external_mutation_authorized=False,
            attempts=attempts,
            error=error,
            evidence_refs=evidence_refs,
        )

    def run_once(self, *, job_id: str | None = None) -> WorkerResult:
        task = self.store.claim_next(
            self.worker_id, lease_seconds=self.lease_seconds, job_id=job_id
        )
        if task is None:
            return self._result("idle")

        job_id = task["job_id"]
        lease_token = task["lease_token"]
        payload = task.get("payload_json")
        if isinstance(payload, str):
            import json

            payload = json.loads(payload)
        if not isinstance(payload, dict):
            return self._fail(job_id, lease_token, "invalid task payload")

        handler_name = payload.get("handler")
        handler = self.handlers.get(handler_name) if isinstance(handler_name, str) else None
        if handler is None:
            return self._fail(job_id, lease_token, "missing approved task handler")

        try:
            self.store.save_checkpoint(
                job_id,
                {"state": "executing", "worker_id": self.worker_id},
                worker_id=self.worker_id,
                lease_token=lease_token,
            )
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="cknexus-worker") as executor:
                future = executor.submit(handler, payload)
                try:
                    output = future.result(timeout=self.execution_timeout)
                except TimeoutError as exc:
                    future.cancel()
                    raise TimeoutError(f"handler timeout after {self.execution_timeout}s") from exc
            if not isinstance(output, dict):
                raise TypeError("task handler must return a mapping")
            evidence_refs = tuple(output.get("evidence_refs") or ())
            test_ok = bool(output.get("ok"))
            security_ok = bool(output.get("security_ok", True))
            self.store.save_checkpoint(
                job_id,
                {
                    "state": "verifying",
                    "worker_id": self.worker_id,
                    "evidence_refs": list(evidence_refs),
                },
                worker_id=self.worker_id,
                lease_token=lease_token,
            )
        except Exception as exc:
            return self._fail(job_id, lease_token, str(exc))

        verification = self.verifier.evaluate(
            state="EXECUTED_UNVERIFIED",
            test_ok=test_ok,
            security_ok=security_ok,
            evidence_refs=evidence_refs,
        )
        attempts = verification.attempts

        if not verification.release_evidence:
            repair = output.get("repair")

            def verify(attempt: int) -> bool:
                nonlocal attempts
                attempts = attempt
                self.store.save_checkpoint(
                    job_id,
                    {"state": "repairing", "attempt": attempt},
                    worker_id=self.worker_id,
                    lease_token=lease_token,
                )
                if attempt <= self.verifier.max_repairs and callable(repair):
                    repair(attempt)
                return bool(output.get("repair_ok", False))

            verification = self.verifier.repair_loop(
                verify=verify,
                evidence_refs=evidence_refs,
            )
            attempts = max(
                attempts, verification.attempts + (1 if verification.attempts == 0 else 0)
            )

        if verification.release_evidence:
            try:
                self.store.save_checkpoint(
                    job_id,
                    {"state": "completed", "evidence_refs": list(verification.evidence_refs)},
                    worker_id=self.worker_id,
                    lease_token=lease_token,
                )
                self.store.finish(
                    job_id,
                    success=True,
                    result={
                        "evidence_refs": list(verification.evidence_refs),
                        "release_evidence": True,
                        "production_status": "NO-GO",
                        "external_mutation_authorized": False,
                    },
                    worker_id=self.worker_id,
                    lease_token=lease_token,
                )
            except ValueError as exc:
                return self._result(
                    "failed", attempts=attempts, error=str(exc), evidence_refs=evidence_refs
                )
            return self._result(
                "completed",
                attempts=attempts,
                evidence_refs=verification.evidence_refs,
                release_evidence=True,
            )

        return self._fail(
            job_id,
            lease_token,
            "verification failed or repair budget exhausted",
            attempts=attempts,
            evidence_refs=evidence_refs,
        )

    def _fail(
        self,
        job_id: str,
        lease_token: str,
        error: str,
        *,
        attempts: int = 0,
        evidence_refs: tuple[str, ...] = (),
    ) -> WorkerResult:
        try:
            self.store.save_checkpoint(
                job_id,
                {"state": "failed", "error": error},
                worker_id=self.worker_id,
                lease_token=lease_token,
            )
            self.store.finish(
                job_id,
                success=False,
                error=error,
                result={
                    "release_evidence": False,
                    "production_status": "NO-GO",
                    "external_mutation_authorized": False,
                },
                worker_id=self.worker_id,
                lease_token=lease_token,
            )
        except ValueError as exc:
            return self._result(
                "failed", attempts=attempts, error=str(exc), evidence_refs=evidence_refs
            )
        return self._result("failed", attempts=attempts, error=error, evidence_refs=evidence_refs)
