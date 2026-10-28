"""Deterministic runtime judgment gate for verified CK-NEXUS GitOps evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

JudgmentAction = Literal["allow", "edit", "escalate", "deny"]

# Exact sensitive targets plus path components; no substring-only matching.
_CRITICAL_EXACT = {
    "/etc/systemd/system/n8n.service",
    "etc/systemd/system/n8n.service",
    "credentials.json",
    ".env",
}
_CRITICAL_COMPONENTS = {
    "api_key",
    "api-key",
    "credentials",
    "credentials.json",
    "secrets",
    ".ssh",
    "id_rsa",
    "id_ed25519",
    "private_keys",
}


@dataclass(frozen=True, slots=True)
class JudgmentResult:
    action: JudgmentAction
    reason: str
    trace_level: int


class JudgmentGate:
    """Apply deterministic policy before a verified branch may be published."""

    def evaluate(
        self,
        state: str,
        tests_ok: bool,
        changed_paths: list[str],
        error_reason: str | None = None,
    ) -> JudgmentResult:
        paths = [p.replace("\\", "/").strip() for p in changed_paths if isinstance(p, str)]
        for path in paths:
            normalized = path.lstrip("./")
            components = {part.lower() for part in normalized.split("/") if part}
            if (
                path in _CRITICAL_EXACT
                or normalized in _CRITICAL_EXACT
                or components & _CRITICAL_COMPONENTS
            ):
                return JudgmentResult("deny", "critical_path_change_denied", 5)
            if path.startswith("/") or ".." in path.split("/"):
                return JudgmentResult("deny", "unsafe_path_denied", 5)

        error_code = (error_reason or "").lower()
        if (
            error_code in {"authentication_failure", "http_401", "unauthorized"}
            or "401" in error_code
            or "unauthorized" in error_code
        ):
            return JudgmentResult("escalate", "authentication_failure_requires_human", 3)
        if state in {"blocked", "failed", "verification_failed"}:
            return JudgmentResult("escalate", "task_requires_human_review", 3)
        if state == "verified" and not tests_ok:
            return JudgmentResult("edit", "tests_not_passing_no_publish", 2)
        if state == "verified" and tests_ok:
            return JudgmentResult("allow", "verified_tests_passed", 1)
        return JudgmentResult("deny", "unknown_state_denied", 4)
