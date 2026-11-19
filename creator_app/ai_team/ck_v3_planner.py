"""Deterministic, non-executing planner for CK_v3 bounded work packets.

The planner converts one already policy-valid CK_v3 WorkPacket into an evidence-oriented plan. It
never invokes tools, opens network connections, reads credentials, merges code, deploys, or mutates
production. CK-NEXUS remains the execution and policy authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from creator_app.ai_team.ck_coordination import CKRole, CoordinationPolicy, WorkPacket

_FORBIDDEN_ACTION_FRAGMENTS = (
    "production mutation",
    "deploy production",
    "production deploy",
    "credential access",
    "credential export",
    "export token",
    "export secret",
    "external write",
    "merge pr #14",
    "merge pull request #14",
    "override policy",
    "override permission",
)


@dataclass(frozen=True, slots=True)
class PlannedStep:
    """One non-authoritative development step and the evidence it must emit."""

    step_id: str
    action: str
    evidence_required: tuple[str, ...]
    read_only_default: bool = True
    external_write: bool = False
    credential_access: bool = False
    production_mutation: bool = False


@dataclass(frozen=True, slots=True)
class CKV3ExecutionPlan:
    """A plan candidate. Possession of a plan never grants execution authority."""

    task_id: str
    target: str
    source_commit: str
    steps: tuple[PlannedStep, ...]
    denied_actions: tuple[str, ...]
    requires_independent_verification: bool = True
    execution_authority: bool = False


class CKV3Planner:
    """Compile bounded CK_v3 work into a deterministic evidence-first plan."""

    @staticmethod
    def compile(packet: WorkPacket) -> CKV3ExecutionPlan:
        CoordinationPolicy.validate_packet(packet)
        if packet.assignee is not CKRole.CK_V3:
            raise ValueError("ck_v3_packet_required")
        if packet.source_commit is None or not _is_full_sha1(packet.source_commit):
            raise ValueError("exact_source_commit_required")
        if not packet.allowed_actions:
            raise ValueError("allowed_actions_required")

        normalized_actions = tuple(_validate_action(action) for action in packet.allowed_actions)
        evidence = tuple(item.strip() for item in packet.expected_evidence if item.strip())
        if not evidence:
            raise ValueError("expected_evidence_required")

        steps = tuple(
            PlannedStep(
                step_id=f"{packet.task_id}-S{index:02d}",
                action=action,
                evidence_required=evidence,
            )
            for index, action in enumerate(normalized_actions, start=1)
        )
        return CKV3ExecutionPlan(
            task_id=packet.task_id,
            target=packet.target,
            source_commit=packet.source_commit.lower(),
            steps=steps,
            denied_actions=packet.denied_actions,
        )


def _is_full_sha1(value: str) -> bool:
    normalized = value.lower()
    return len(normalized) == 40 and all(char in "0123456789abcdef" for char in normalized)


def _validate_action(action: str) -> str:
    normalized = " ".join(action.strip().split())
    if not normalized:
        raise ValueError("empty_allowed_action")
    lowered = normalized.lower()
    if any(fragment in lowered for fragment in _FORBIDDEN_ACTION_FRAGMENTS):
        raise ValueError("forbidden_action_in_allowed_set")
    return normalized
