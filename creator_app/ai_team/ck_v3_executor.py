"""Fail-closed CK_v3 adapter for an exact attested read-only tool registry.

The adapter does not grant authority. It consumes an already bounded CK_v3 execution plan plus a
short-lived CK-NEXUS execution grant, rechecks exact source/runtime identity, and may invoke only the
six CK-owned clean-room read-only tools through an injected invoker.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from creator_app.ai_team.ck_v3_planner import CKV3ExecutionPlan, PlannedStep
from creator_app.device_bridge.mcp_server_v2 import TOOL_NAMES

_MAX_ARGUMENT_BYTES = 8 * 1024
_MAX_RESULT_BYTES = 16 * 1024
_MAX_GRANT_TTL_SECONDS = 10 * 60
_CLOCK_SKEW_SECONDS = 60
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")
_SENSITIVE_ARGUMENT_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "cookie",
        "credential",
        "credentials",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
)


class ExecutionPolicyError(ValueError):
    """Raised when CK_v3 execution would violate a CK-NEXUS boundary."""


class ExecutionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class ReadOnlyToolInvoker(Protocol):
    """Minimal injected interface for a CK-owned read-only tool runtime."""

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call one already-attested tool."""


@dataclass(frozen=True, slots=True)
class CKV3ExecutionGrant:
    """Short-lived, non-secret CK-NEXUS capability envelope for one CK_v3 task."""

    grant_id: str
    task_id: str
    source_commit: str
    source_tree: str
    registry_sha256: str
    allowed_tools: tuple[str, ...]
    issued_at_unix: int
    expires_at_unix: int
    read_only: bool = True
    credential_access: bool = False
    external_write: bool = False
    production_mutation: bool = False

    def validate(self, *, now_unix: int | None = None) -> CKV3ExecutionGrant:
        now = int(time.time()) if now_unix is None else now_unix
        if not _SAFE_ID.fullmatch(self.grant_id):
            raise ExecutionPolicyError("grant_id_invalid")
        if not _SAFE_ID.fullmatch(self.task_id):
            raise ExecutionPolicyError("task_id_invalid")
        _require_hex(self.source_commit, 40, "source_commit_invalid")
        _require_hex(self.source_tree, 40, "source_tree_invalid")
        _require_hex(self.registry_sha256, 64, "registry_sha256_invalid")
        if not self.allowed_tools:
            raise ExecutionPolicyError("allowed_tools_required")
        if any(tool not in TOOL_NAMES for tool in self.allowed_tools):
            raise ExecutionPolicyError("noncanonical_tool_in_grant")
        if len(set(self.allowed_tools)) != len(self.allowed_tools):
            raise ExecutionPolicyError("duplicate_tool_in_grant")
        if not self.read_only:
            raise ExecutionPolicyError("read_only_grant_required")
        if self.credential_access:
            raise ExecutionPolicyError("credential_access_denied")
        if self.external_write:
            raise ExecutionPolicyError("external_write_denied")
        if self.production_mutation:
            raise ExecutionPolicyError("production_mutation_denied")
        if self.issued_at_unix > now + _CLOCK_SKEW_SECONDS:
            raise ExecutionPolicyError("grant_issued_in_future")
        if self.expires_at_unix <= now:
            raise ExecutionPolicyError("grant_expired")
        ttl = self.expires_at_unix - self.issued_at_unix
        if not 1 <= ttl <= _MAX_GRANT_TTL_SECONDS:
            raise ExecutionPolicyError("grant_ttl_invalid")
        return self


@dataclass(frozen=True, slots=True)
class ExecutionEvidence:
    """Bounded evidence that intentionally excludes tool arguments and raw secrets."""

    evidence_id: str
    grant_id: str
    task_id: str
    step_id: str
    tool_name: str
    source_commit: str
    source_tree: str
    registry_sha256: str
    status: ExecutionStatus
    result_sha256: str
    result_bytes: int
    duration_ms: int
    error: str | None = None


@dataclass(frozen=True, slots=True)
class CKV3ExecutionResult:
    ok: bool
    output: Any
    evidence: ExecutionEvidence


class CKV3ReadOnlyExecutor:
    """Execute one explicit `tool:<name>` plan step after exact grant reconciliation."""

    async def execute(
        self,
        *,
        plan: CKV3ExecutionPlan,
        step_id: str,
        arguments: dict[str, Any],
        grant: CKV3ExecutionGrant,
        current_source_commit: str,
        current_source_tree: str,
        current_registry_sha256: str,
        invoker: ReadOnlyToolInvoker,
        now_unix: int | None = None,
    ) -> CKV3ExecutionResult:
        now = int(time.time()) if now_unix is None else now_unix
        grant.validate(now_unix=now)
        self._validate_plan_and_runtime(
            plan=plan,
            grant=grant,
            current_source_commit=current_source_commit,
            current_source_tree=current_source_tree,
            current_registry_sha256=current_registry_sha256,
        )
        step = _find_step(plan, step_id)
        tool_name = _tool_name_from_step(step)
        if tool_name not in grant.allowed_tools:
            raise ExecutionPolicyError("tool_not_granted")

        argument_bytes = _canonical_json_bytes(arguments, "arguments_not_json_serializable")
        if len(argument_bytes) > _MAX_ARGUMENT_BYTES:
            raise ExecutionPolicyError("tool_arguments_too_large")
        if _contains_sensitive_argument_key(arguments):
            raise ExecutionPolicyError("sensitive_argument_key_denied")

        started = time.monotonic()
        try:
            output = await invoker.call_tool(tool_name, arguments)
        except Exception:
            duration_ms = max(0, int((time.monotonic() - started) * 1000))
            return _failed_result(
                grant=grant,
                step=step,
                tool_name=tool_name,
                duration_ms=duration_ms,
                reason="tool_call_failed_closed",
            )

        duration_ms = max(0, int((time.monotonic() - started) * 1000))
        try:
            output_bytes = _canonical_json_bytes(output, "tool_result_not_json_serializable")
        except ExecutionPolicyError:
            return _failed_result(
                grant=grant,
                step=step,
                tool_name=tool_name,
                duration_ms=duration_ms,
                reason="tool_result_not_json_serializable",
            )
        if len(output_bytes) > _MAX_RESULT_BYTES:
            return _failed_result(
                grant=grant,
                step=step,
                tool_name=tool_name,
                duration_ms=duration_ms,
                reason="tool_result_too_large",
                result_bytes=len(output_bytes),
                result_sha256=hashlib.sha256(output_bytes).hexdigest(),
            )

        result_sha256 = hashlib.sha256(output_bytes).hexdigest()
        evidence = _evidence(
            grant=grant,
            step=step,
            tool_name=tool_name,
            status=ExecutionStatus.PASS,
            result_sha256=result_sha256,
            result_bytes=len(output_bytes),
            duration_ms=duration_ms,
            error=None,
        )
        return CKV3ExecutionResult(ok=True, output=output, evidence=evidence)

    @staticmethod
    def _validate_plan_and_runtime(
        *,
        plan: CKV3ExecutionPlan,
        grant: CKV3ExecutionGrant,
        current_source_commit: str,
        current_source_tree: str,
        current_registry_sha256: str,
    ) -> None:
        if plan.execution_authority:
            raise ExecutionPolicyError("plan_must_not_claim_execution_authority")
        if not plan.requires_independent_verification:
            raise ExecutionPolicyError("independent_verification_required")
        if plan.task_id != grant.task_id:
            raise ExecutionPolicyError("grant_task_mismatch")
        if plan.source_commit != grant.source_commit.lower():
            raise ExecutionPolicyError("grant_source_commit_mismatch")
        if current_source_commit.lower() != grant.source_commit.lower():
            raise ExecutionPolicyError("stale_source_commit")
        if current_source_tree.lower() != grant.source_tree.lower():
            raise ExecutionPolicyError("stale_source_tree")
        if current_registry_sha256.lower() != grant.registry_sha256.lower():
            raise ExecutionPolicyError("stale_runtime_registry")


def _find_step(plan: CKV3ExecutionPlan, step_id: str) -> PlannedStep:
    for step in plan.steps:
        if step.step_id == step_id:
            return step
    raise ExecutionPolicyError("plan_step_not_found")


def _tool_name_from_step(step: PlannedStep) -> str:
    if not step.read_only_default:
        raise ExecutionPolicyError("read_only_step_required")
    if step.external_write or step.credential_access or step.production_mutation:
        raise ExecutionPolicyError("unsafe_step_flags")
    if not step.action.startswith("tool:"):
        raise ExecutionPolicyError("explicit_tool_action_required")
    tool_name = step.action.removeprefix("tool:").strip()
    if not tool_name or any(char.isspace() for char in tool_name):
        raise ExecutionPolicyError("tool_action_invalid")
    if tool_name not in TOOL_NAMES:
        raise ExecutionPolicyError("tool_not_canonical_read_only")
    return tool_name


def _require_hex(value: str, length: int, reason: str) -> None:
    normalized = value.lower()
    if len(normalized) != length or any(char not in "0123456789abcdef" for char in normalized):
        raise ExecutionPolicyError(reason)


def _canonical_json_bytes(value: Any, reason: str) -> bytes:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ExecutionPolicyError(reason) from exc
    return encoded


def _contains_sensitive_argument_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str):
                return True
            normalized = key.strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_ARGUMENT_KEYS:
                return True
            if _contains_sensitive_argument_key(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_contains_sensitive_argument_key(item) for item in value)
    return False


def _failed_result(
    *,
    grant: CKV3ExecutionGrant,
    step: PlannedStep,
    tool_name: str,
    duration_ms: int,
    reason: str,
    result_bytes: int = 0,
    result_sha256: str | None = None,
) -> CKV3ExecutionResult:
    safe_output = {"ok": False, "error": reason}
    digest = result_sha256 or hashlib.sha256(_canonical_json_bytes(safe_output, "internal")).hexdigest()
    evidence = _evidence(
        grant=grant,
        step=step,
        tool_name=tool_name,
        status=ExecutionStatus.FAIL,
        result_sha256=digest,
        result_bytes=result_bytes,
        duration_ms=duration_ms,
        error=reason,
    )
    return CKV3ExecutionResult(ok=False, output=safe_output, evidence=evidence)


def _evidence(
    *,
    grant: CKV3ExecutionGrant,
    step: PlannedStep,
    tool_name: str,
    status: ExecutionStatus,
    result_sha256: str,
    result_bytes: int,
    duration_ms: int,
    error: str | None,
) -> ExecutionEvidence:
    material = "|".join(
        (
            grant.grant_id,
            grant.task_id,
            step.step_id,
            tool_name,
            grant.source_commit.lower(),
            grant.source_tree.lower(),
            grant.registry_sha256.lower(),
            status.value,
            result_sha256,
        )
    ).encode("utf-8")
    evidence_id = f"evd_{hashlib.sha256(material).hexdigest()[:24]}"
    return ExecutionEvidence(
        evidence_id=evidence_id,
        grant_id=grant.grant_id,
        task_id=grant.task_id,
        step_id=step.step_id,
        tool_name=tool_name,
        source_commit=grant.source_commit.lower(),
        source_tree=grant.source_tree.lower(),
        registry_sha256=grant.registry_sha256.lower(),
        status=status,
        result_sha256=result_sha256,
        result_bytes=result_bytes,
        duration_ms=duration_ms,
        error=error,
    )