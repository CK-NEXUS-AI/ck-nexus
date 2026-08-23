"""Runtime-aware polyglot toolchain registry.

Discovery is explicit and local. A language is not considered usable merely
because a model knows its syntax; required toolchain components must be found
and may then be promoted from AVAILABLE to VERIFIED by higher-level checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from shutil import which


class ToolchainStatus(str, Enum):
    MISSING = "MISSING"
    AVAILABLE = "AVAILABLE"
    QUARANTINED = "QUARANTINED"
    VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class ToolSpec:
    name: str
    command: str
    role: str


@dataclass
class LanguageToolchain:
    language: str
    tools: list[ToolSpec] = field(default_factory=list)
    status: ToolchainStatus = ToolchainStatus.MISSING
    discovered: dict[str, str | None] = field(default_factory=dict)

    def probe(self) -> ToolchainStatus:
        self.discovered = {tool.name: which(tool.command) for tool in self.tools}
        self.status = (
            ToolchainStatus.AVAILABLE
            if self.tools and all(self.discovered.values())
            else ToolchainStatus.MISSING
        )
        return self.status


class ToolchainRegistry:
    def __init__(self) -> None:
        self._items: dict[str, LanguageToolchain] = {}

    def register(self, toolchain: LanguageToolchain) -> None:
        self._items[toolchain.language.lower()] = toolchain

    def get(self, language: str) -> LanguageToolchain | None:
        return self._items.get(language.lower())

    def probe(self, language: str) -> ToolchainStatus:
        item = self.get(language)
        if item is None:
            return ToolchainStatus.MISSING
        return item.probe()

    def snapshot(self) -> dict[str, dict[str, object]]:
        return {
            name: {
                "status": item.status.value,
                "tools": [tool.__dict__ for tool in item.tools],
                "discovered": dict(item.discovered),
            }
            for name, item in sorted(self._items.items())
        }


def default_registry() -> ToolchainRegistry:
    registry = ToolchainRegistry()
    registry.register(LanguageToolchain("python", [
        ToolSpec("python", "python", "interpreter"),
    ]))
    registry.register(LanguageToolchain("rust", [
        ToolSpec("rustc", "rustc", "compiler"),
        ToolSpec("cargo", "cargo", "package_manager"),
    ]))
    registry.register(LanguageToolchain("go", [
        ToolSpec("go", "go", "compiler_package_manager"),
    ]))
    registry.register(LanguageToolchain("typescript", [
        ToolSpec("node", "node", "runtime"),
        ToolSpec("tsc", "tsc", "compiler"),
    ]))
    return registry
