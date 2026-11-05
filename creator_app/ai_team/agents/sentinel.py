"""Sentinel — fail-closed structural evidence checker.

Sentinel checks evidence-bundle structure and subject binding only. It does not
fetch artifacts, recompute artifact digests, verify signatures, or replace
CK-NEXUS Core/L3 or an independent human reviewer.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from creator_app.ai_team.agent import Agent
from creator_app.ai_team.agent_models import (
    AgentCapability,
    AgentRole,
    TaskResult,
    TaskStatus,
    TeamRequest,
    generate_id,
)

_SHA1_OR_SHA256 = re.compile(r"^(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class SentinelAgent(Agent):
    """ตรวจโครงสร้าง evidence bundle แบบ fail-closed โดยไม่อ้างว่า verify provenance."""

    def __init__(self) -> None:
        super().__init__(
            name="Sentinel",
            role=AgentRole.SENTINEL,
            expertise=(
                "evidence structure",
                "subject binding",
                "release gate challenge",
                "fail closed",
            ),
            description="ผู้ตรวจโครงสร้างหลักฐานแบบ read-only — ส่งผล candidate ให้ Core/L3 ตรวจต่อ",
            capabilities=(
                AgentCapability("evidence_structure", "ตรวจโครงสร้าง evidence bundle", level=10),
                AgentCapability("subject_binding", "ตรวจ SHA ของหลักฐานให้ตรงกับเป้าหมาย", level=9),
                AgentCapability(
                    "release_gate_challenge",
                    "บล็อกการสรุป DONE เมื่อหลักฐานไม่พอ",
                    level=10,
                ),
            ),
        )

    def process(
        self, request: TeamRequest, context: dict[str, Any] | None = None
    ) -> TaskResult:
        context = context or {}
        bundle = context.get("evidence_bundle")
        if not isinstance(bundle, dict):
            return self._blocked(
                request,
                "MISSING",
                "ไม่พบ evidence_bundle — NO EVIDENCE → NO DONE",
                missing=("evidence_bundle",),
            )

        subject_sha = str(bundle.get("subject_sha", "")).strip().lower()
        source = str(bundle.get("source", "")).strip()
        observed_at = str(bundle.get("observed_at", "")).strip()
        checks = bundle.get("checks")
        missing: list[str] = []

        if not _SHA1_OR_SHA256.fullmatch(subject_sha):
            missing.append("subject_sha (40/64 hex characters)")
        if not source:
            missing.append("source")
        try:
            timestamp = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                missing.append("observed_at timezone")
        except ValueError:
            missing.append("observed_at (ISO-8601 with timezone)")
        if not isinstance(checks, list) or not checks:
            missing.append("checks (non-empty list)")

        normalized_checks: list[tuple[str, str]] = []
        if isinstance(checks, list):
            for index, item in enumerate(checks):
                prefix = f"checks[{index}]"
                if not isinstance(item, dict):
                    missing.append(f"{prefix} object")
                    continue
                name = str(item.get("name", "")).strip()
                status = str(item.get("status", "")).strip().upper()
                evidence_ref = str(item.get("evidence_ref", "")).strip()
                check_sha = str(item.get("subject_sha", "")).strip().lower()
                artifact_sha = str(item.get("artifact_sha256", "")).strip()
                if not name:
                    missing.append(f"{prefix}.name")
                if status not in {"PASS", "FAIL", "UNKNOWN"}:
                    missing.append(f"{prefix}.status")
                if not evidence_ref:
                    missing.append(f"{prefix}.evidence_ref")
                if not subject_sha or check_sha != subject_sha:
                    missing.append(f"{prefix}.subject_sha must match bundle subject")
                if not _SHA256.fullmatch(artifact_sha):
                    missing.append(f"{prefix}.artifact_sha256")
                if name and status in {"PASS", "FAIL", "UNKNOWN"}:
                    normalized_checks.append((name, status))

        if missing:
            return self._blocked(
                request,
                "INCOMPLETE",
                "Evidence bundle ไม่ครบหรือผูกกับ subject SHA ไม่ตรงกัน",
                missing=tuple(missing),
                subject_sha=subject_sha or None,
            )

        failed = [name for name, status in normalized_checks if status == "FAIL"]
        unknown = [name for name, status in normalized_checks if status == "UNKNOWN"]
        if failed:
            return TaskResult(
                task_id=generate_id("sentinel"),
                agent_name=self.name,
                agent_role=self.role.value,
                status=TaskStatus.FAILED,
                output="พบ check ที่ไม่ผ่าน: " + ", ".join(failed),
                confidence=0.95,
                warnings=("Release gate ต้องคงสถานะ NO-GO จนกว่าจะมีผลตรวจใหม่",),
                metadata={"evidence_status": "FAILED_CHECKS", "failed_checks": failed},
            )
        if unknown:
            return self._blocked(
                request,
                "INCONCLUSIVE",
                "มี check ที่ยังไม่ทราบผล: " + ", ".join(unknown),
                subject_sha=subject_sha,
            )

        return self._blocked(
            request,
            "CANDIDATE_UNVERIFIED",
            (
                "Evidence bundle ครบในเชิงโครงสร้าง แต่ยังยืนยันแหล่งที่มา/ลายเซ็นกับ "
                "CK-NEXUS Core/L3 ไม่ได้ จึงห้ามสรุป VERIFIED หรือ DONE"
            ),
            subject_sha=subject_sha,
            checks_total=len(normalized_checks),
            source=source,
            verification_scope="STRUCTURE_ONLY",
            artifact_digest_verified=False,
            authority_attestation_verified=False,
        )

    def _blocked(
        self,
        request: TeamRequest,
        evidence_status: str,
        message: str,
        *,
        missing: tuple[str, ...] = (),
        **metadata: Any,
    ) -> TaskResult:
        warnings = ("Sentinel เป็นผู้ตรวจแบบ read-only; ไม่มีอำนาจแทน CK-NEXUS Core/L3",)
        if missing:
            warnings += ("ข้อมูลที่ขาด: " + "; ".join(missing),)
        return TaskResult(
            task_id=generate_id("sentinel"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.BLOCKED,
            output=f"{message} | คำขอ: {request.description[:120]}",
            confidence=0.95 if evidence_status == "CANDIDATE_UNVERIFIED" else 0.2,
            warnings=warnings,
            metadata={"evidence_status": evidence_status, **metadata},
        )
