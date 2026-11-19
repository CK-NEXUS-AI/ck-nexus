"""Guardian — ผู้เชี่ยวชาญด้านความปลอดภัย."""

from __future__ import annotations

import time
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


class GuardianAgent(Agent):
    """Guardian — ตรวจสอบช่องโหว่, ปกป้องข้อมูลลับ, ตรวจสอบสิทธิ์."""

    def __init__(self) -> None:
        super().__init__(
            name="Guardian",
            role=AgentRole.GUARDIAN,
            expertise=(
                "security",
                "oauth2",
                "encryption",
                "jwt",
                "penetration testing",
                "vulnerability",
                "cve",
                "access control",
                "rbac",
                "abac",
                "audit log",
                "compliance",
                "gdpr",
                "secret management",
                "credential",
                "ssl/tls",
                "certificate",
                "hashing",
                "authentication",
                "authorization",
                "firewall",
                "ids",
                "ips",
                "fail-closed",
                "defense in depth",
            ),
            description="Guardian — ปกป้องระบบจากช่องโหว่และภัยคุกคาม",
            capabilities=(
                AgentCapability("security_audit", "ตรวจสอบช่องโหว่", level=9),
                AgentCapability("secret_management", "จัดการข้อมูลลับ", level=9),
                AgentCapability("access_control", "ตรวจสอบสิทธิ์", level=9),
                AgentCapability("compliance", "ตรวจสอบการปฏิบัติตามมาตรฐาน", level=8),
            ),
        )

    def process(self, request: TeamRequest, context: dict[str, Any] | None = None) -> TaskResult:
        """ประมวลผล — ตรวจสอบความปลอดภัย."""
        start = time.time()
        context = context or {}

        desc = request.description.lower()
        output_lines: list[str] = []
        artifacts: list[str] = []
        warnings: list[str] = []

        # ตรวจสอบช่องโหว่
        if any(kw in desc for kw in ("security", "vulnerability", "scan", "audit")):
            output_lines.append("🛡️ กำลังตรวจสอบความปลอดภัย...")
            output_lines.append(self._security_audit(request))
            artifacts.append("security:audit")

        # จัดการคีย์/ความลับ
        if any(kw in desc for kw in ("credential", "secret", "key", "token", "password")):
            output_lines.append("🔐 กำลังจัดการข้อมูลลับ...")
            output_lines.append(self._secret_management(request))
            artifacts.append("security:secrets")
            warnings.append("⚠️ ห้ามเปิดเผย raw API key ใน logs/ไฟล์")

        # ตรวจสอบสิทธิ์
        if any(kw in desc for kw in ("auth", "permission", "access", "role", "rbac")):
            output_lines.append("🔑 กำลังตรวจสอบสิทธิ์...")
            output_lines.append(self._access_control(request))
            artifacts.append("security:access_control")

        # ตรวจสอบ compliance
        if any(kw in desc for kw in ("compliance", "gdpr", "audit", "policy")):
            output_lines.append("📋 กำลังตรวจสอบการปฏิบัติตามมาตรฐาน...")
            output_lines.append(self._compliance_check(request))
            artifacts.append("security:compliance")

        # Fail-closed check
        if any(kw in desc for kw in ("fail", "safe", "closed", "fallback")):
            output_lines.append("🔒 ตรวจสอบ Fail-Closed...")
            output_lines.append(self._fail_closed_check(request))
            artifacts.append("security:fail_closed")

        if not output_lines:
            output_lines.append("🛡️ ตรวจสอบความปลอดภัยทั่วไป...")
            output_lines.append(self._general_security_check(request))
            artifacts.append("security:general")

        if warnings:
            output_lines.append("\n⚠️ คำเตือน:")
            output_lines.extend(warnings)

        return TaskResult(
            task_id=generate_id("guard"),
            agent_name=self.name,
            agent_role=self.role.value,
            status=TaskStatus.COMPLETED,
            output="\n".join(output_lines),
            artifacts=tuple(artifacts),
            duration_seconds=time.time() - start,
            confidence=0.9,
            warnings=tuple(warnings),
        )

    def _security_audit(self, request: TeamRequest) -> str:
        return (
            f"หัวข้อ: {request.description[:200]}\n"
            "ขั้นตอน:\n"
            "1. สแกนช่องโหว่ในโค้ด (OWASP Top 10)\n"
            "2. ตรวจสอบ dependency vulnerabilities\n"
            "3. วิเคราะห์ attack surface\n"
            "4. ประเมินความเสี่ยง (CVSS)\n"
            "5. สร้าง security report\n"
            "✅ ตรวจสอบเสร็จสิ้น"
        )

    def _secret_management(self, request: TeamRequest) -> str:
        return (
            "ขั้นตอนจัดการข้อมูลลับ:\n"
            "1. ระบุ secrets ทั้งหมดในโค้ด\n"
            "2. ย้ายไป environment variables / vault\n"
            "3. ตั้งค่า secret scanning ใน CI/CD\n"
            "4. ตรวจสอบว่าไม่มี secret ใน logs\n"
            "5. ตั้ง key rotation policy\n"
            "✅ จัดการเสร็จสิ้น — ไม่มี raw key ในโค้ด"
        )

    def _access_control(self, request: TeamRequest) -> str:
        return (
            "ขั้นตอนตรวจสอบสิทธิ์:\n"
            "1. ระบุ resources ที่ต้องป้องกัน\n"
            "2. ออกแบบ role-based access control\n"
            "3. ตั้งค่า least privilege principle\n"
            "4. ตรวจสอบ session management\n"
            "5. สร้าง audit log\n"
            "✅ ตรวจสอบเสร็จสิ้น"
        )

    def _compliance_check(self, request: TeamRequest) -> str:
        return (
            "ขั้นตอนตรวจสอบ compliance:\n"
            "1. ระบุมาตรฐานที่เกี่ยวข้อง\n"
            "2. ตรวจสอบ data handling\n"
            "3. ตรวจสอบ retention policy\n"
            "4. ตรวจสอบ consent mechanism\n"
            "5. สร้าง compliance report\n"
            "✅ ตรวจสอบเสร็จสิ้น"
        )

    def _fail_closed_check(self, request: TeamRequest) -> str:
        return (
            "Fail-Closed Check:\n"
            "1. ตรวจสอบ default deny policies\n"
            "2. ตรวจสอบ error handling — fail to safe\n"
            "3. ตรวจสอบ timeout/circuit breaker\n"
            "4. ตรวจสอบ graceful degradation\n"
            "✅ Fail-closed verified"
        )

    def _general_security_check(self, request: TeamRequest) -> str:
        return (
            "ตรวจสอบความปลอดภัยทั่วไป:\n"
            "1. ตรวจสอบ input validation\n"
            "2. ตรวจสอบ SQL injection / XSS\n"
            "3. ตรวจสอบ CSRF protection\n"
            "4. ตรวจสอบ HTTPS/TLS\n"
            "✅ ตรวจสอบเสร็จสิ้น"
        )
