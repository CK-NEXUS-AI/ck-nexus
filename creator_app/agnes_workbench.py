from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class WorkspaceKind(StrEnum):
    LOCAL = "local"
    E2B = "e2b"
    GITHUB_CODESPACES = "github_codespaces"
    DAYTONA = "daytona"


@dataclass(frozen=True, slots=True)
class WorkspaceProviderSpec:
    kind: WorkspaceKind
    isolated: bool
    terminal: bool
    filesystem: bool
    git: bool
    external: bool
    auth_boundary: str
    default_enabled: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "isolated": self.isolated,
            "terminal": self.terminal,
            "filesystem": self.filesystem,
            "git": self.git,
            "external": self.external,
            "auth_boundary": self.auth_boundary,
            "default_enabled": self.default_enabled,
        }


PROVIDERS: tuple[WorkspaceProviderSpec, ...] = (
    WorkspaceProviderSpec(
        WorkspaceKind.LOCAL, True, True, True, True, False,
        "local process sandbox; no provider credential", True,
    ),
    WorkspaceProviderSpec(
        WorkspaceKind.E2B, True, True, True, True, True,
        "service credential held by workspace broker; never exposed to AGNES", False,
    ),
    WorkspaceProviderSpec(
        WorkspaceKind.GITHUB_CODESPACES, True, True, True, True, True,
        "GitHub App/user authorization held by GitHub integration; least privilege", False,
    ),
    WorkspaceProviderSpec(
        WorkspaceKind.DAYTONA, True, True, True, True, True,
        "service credential held by workspace broker; never exposed to AGNES", False,
    ),
)


class WorkspaceBroker:
    """Provider-neutral registry. Live external creation remains behind explicit approval/auth."""

    def providers(self) -> tuple[WorkspaceProviderSpec, ...]:
        return PROVIDERS

    def plan(self, *, preferred: WorkspaceKind = WorkspaceKind.LOCAL) -> dict[str, object]:
        selected = next((item for item in PROVIDERS if item.kind is preferred), PROVIDERS[0])
        return {
            "selected": selected.as_dict(),
            "steps": [
                "create isolated workspace from exact baseline commit",
                "create feature branch; never rewrite protected history",
                "mount only approved files/resources",
                "expose only task-scoped skills/tools",
                "run bounded commands with timeout and output limits",
                "compile and test",
                "run defensive security/secret scans",
                "produce diff, evidence, and rollback plan",
                "stop before merge/deploy if approval is required",
            ],
        }
