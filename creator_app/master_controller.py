"""Deterministic command planner for the CK-NEXUS control plane."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ToolLane(StrEnum):
    GITHUB = "github"
    VPS_DOCKER = "vps_docker"
    WEB_RESEARCH = "web_research"
    FILE_CONTENT = "file_content"
    GMAIL = "gmail"
    AGNES = "agnes"
    EVIDENCE = "evidence"


class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    REVERSIBLE_DEV = "reversible_dev"
    EXTERNAL_WRITE = "external_write"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ControllerStep:
    index: int
    lane: ToolLane
    action: str
    required: bool = True
    human_approval_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "lane": self.lane.value,
            "action": self.action,
            "required": self.required,
            "human_approval_required": self.human_approval_required,
        }


@dataclass(frozen=True, slots=True)
class ControllerPlan:
    command: str
    risk: RiskLevel
    lanes: tuple[ToolLane, ...]
    steps: tuple[ControllerStep, ...]
    blockers: tuple[str, ...]
    auto_execute_allowed: bool
    production_effect: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "risk": self.risk.value,
            "lanes": [lane.value for lane in self.lanes],
            "steps": [step.as_dict() for step in self.steps],
            "blockers": list(self.blockers),
            "auto_execute_allowed": self.auto_execute_allowed,
            "production_effect": self.production_effect,
        }


class MasterController:
    """Plan one user command across existing CK-NEXUS capability lanes.

    This planner does not execute external actions. It converts intent into a
    deterministic, least-privilege plan that existing runtimes can consume.
    """

    _PRODUCTION_TERMS = {
        "deploy",
        "deployment",
        "merge",
        "production",
        "release",
        "promote",
        "publish",
        "go-live",
        "go live",
        "ขึ้นโปรดักชัน",
        "โปรดักชัน",
        "ปล่อยจริง",
        "เมิร์จ",
    }
    _EXTERNAL_WRITE_TERMS = {
        "send",
        "reply",
        "email to",
        "submit",
        "purchase",
        "pay",
        "register",
        "สมัคร",
        "ส่งอีเมล",
        "ตอบกลับ",
        "ส่งแบบฟอร์ม",
        "ซื้อ",
        "จ่าย",
    }
    _DEV_TERMS = {
        "code",
        "implement",
        "fix",
        "patch",
        "test",
        "ci",
        "pr",
        "branch",
        "benchmark",
        "develop",
        "พัฒนา",
        "แก้",
        "ทดสอบ",
        "โค้ด",
    }

    _LANE_TERMS: dict[ToolLane, set[str]] = {
        ToolLane.GITHUB: {
            "github",
            "repo",
            "repository",
            "pr",
            "branch",
            "commit",
            "ci",
            "workflow",
            "source",
            "โค้ด",
        },
        ToolLane.VPS_DOCKER: {
            "vps",
            "docker",
            "linux",
            "cgroup",
            "bubblewrap",
            "unshare",
            "q10",
            "codex security",
            "runtime",
            "server",
        },
        ToolLane.WEB_RESEARCH: {
            "research",
            "search",
            "web",
            "official",
            "benchmark",
            "compare",
            "ค้นหา",
            "วิจัย",
            "เปรียบเทียบ",
        },
        ToolLane.FILE_CONTENT: {
            "file",
            "zip",
            "pdf",
            "docx",
            "xlsx",
            "pin",
            "pinterest",
            "image research",
            "ไฟล์",
            "เนื้อหา",
        },
        ToolLane.GMAIL: {
            "gmail",
            "email",
            "mail",
            "reviewer",
            "reconix",
            "schellman",
            "certificate",
            "certification",
            "อีเมล",
            "ผู้ตรวจ",
            "ใบรับรอง",
        },
        ToolLane.AGNES: {
            "agnes",
            "agent",
            "council",
            "planner",
            "orchestration",
            "develop",
            "พัฒนา",
            "วิเคราะห์",
        },
        ToolLane.EVIDENCE: {
            "evidence",
            "proof",
            "hash",
            "sha",
            "verify",
            "verification",
            "audit",
            "q10",
            "หลักฐาน",
            "ตรวจสอบ",
        },
    }

    @staticmethod
    def _normalize(command: str) -> str:
        return " ".join(command.casefold().split())

    @staticmethod
    def _contains(text: str, terms: set[str]) -> bool:
        return any(term in text for term in terms)

    def classify_risk(self, command: str) -> RiskLevel:
        text = self._normalize(command)
        if self._contains(text, self._PRODUCTION_TERMS):
            return RiskLevel.PRODUCTION
        if self._contains(text, self._EXTERNAL_WRITE_TERMS):
            return RiskLevel.EXTERNAL_WRITE
        if self._contains(text, self._DEV_TERMS):
            return RiskLevel.REVERSIBLE_DEV
        return RiskLevel.READ_ONLY

    def select_lanes(self, command: str) -> tuple[ToolLane, ...]:
        text = self._normalize(command)
        lanes = [
            lane
            for lane, terms in self._LANE_TERMS.items()
            if self._contains(text, terms)
        ]

        if not lanes or text in {"ck-nexus run", "ck nexus run", "run"}:
            lanes = [
                ToolLane.GITHUB,
                ToolLane.VPS_DOCKER,
                ToolLane.GMAIL,
                ToolLane.AGNES,
                ToolLane.EVIDENCE,
            ]

        if ToolLane.EVIDENCE not in lanes:
            lanes.append(ToolLane.EVIDENCE)

        order = {lane: index for index, lane in enumerate(ToolLane)}
        return tuple(sorted(set(lanes), key=order.__getitem__))

    def plan(
        self,
        command: str,
        *,
        available_lanes: dict[str, bool] | None = None,
    ) -> ControllerPlan:
        normalized = self._normalize(command)
        if not normalized:
            raise ValueError("command is required")
        if len(command) > 2000:
            raise ValueError("command must be <= 2000 characters")

        risk = self.classify_risk(command)
        lanes = self.select_lanes(command)
        availability = available_lanes or {}

        blockers = tuple(
            f"lane_unavailable:{lane.value}"
            for lane in lanes
            if availability.get(lane.value) is False
        )

        human_gate = risk in {RiskLevel.EXTERNAL_WRITE, RiskLevel.PRODUCTION}
        steps: list[ControllerStep] = []
        action_map = {
            ToolLane.GITHUB: "inspect exact source, PR and CI state",
            ToolLane.VPS_DOCKER: "inspect isolated Linux/Docker runtime readiness",
            ToolLane.WEB_RESEARCH: "research primary or official sources",
            ToolLane.FILE_CONTENT: "extract semantic content and provenance",
            ToolLane.GMAIL: "inspect relevant incoming reviewer/vendor messages",
            ToolLane.AGNES: "deduplicate, classify delta and build bounded plan",
            ToolLane.EVIDENCE: "seal exact results, hashes, failures and blockers",
        }
        for index, lane in enumerate(lanes, start=1):
            steps.append(
                ControllerStep(
                    index=index,
                    lane=lane,
                    action=action_map[lane],
                    human_approval_required=(
                        human_gate
                        and lane
                        in {
                            ToolLane.GITHUB,
                            ToolLane.GMAIL,
                            ToolLane.VPS_DOCKER,
                        }
                    ),
                )
            )

        if human_gate:
            steps.append(
                ControllerStep(
                    index=len(steps) + 1,
                    lane=ToolLane.EVIDENCE,
                    action="stop at human approval boundary before side effect",
                    human_approval_required=True,
                )
            )

        auto_execute_allowed = not blockers and not human_gate
        return ControllerPlan(
            command=command,
            risk=risk,
            lanes=lanes,
            steps=tuple(steps),
            blockers=blockers,
            auto_execute_allowed=auto_execute_allowed,
            production_effect=False,
        )
