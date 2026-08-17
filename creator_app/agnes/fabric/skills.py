"""Fail-closed skill lifecycle and supply-chain contract."""

from dataclasses import dataclass
from typing import Self

from .models import ModuleStage, RiskClass


_ALLOWED: dict[ModuleStage, set[ModuleStage]] = {
    ModuleStage.DISCOVERED: {ModuleStage.INSPECTED, ModuleStage.REVOKED},
    ModuleStage.INSPECTED: {ModuleStage.SCANNED, ModuleStage.REVOKED},
    ModuleStage.SCANNED: {ModuleStage.EVALUATED, ModuleStage.REVOKED},
    ModuleStage.EVALUATED: {ModuleStage.APPROVED, ModuleStage.REVOKED},
    ModuleStage.APPROVED: {ModuleStage.ENABLED_READONLY, ModuleStage.REVOKED},
    ModuleStage.ENABLED_READONLY: {
        ModuleStage.APPROVED_READWRITE,
        ModuleStage.SUSPENDED,
        ModuleStage.REVOKED,
    },
    ModuleStage.APPROVED_READWRITE: {ModuleStage.SUSPENDED, ModuleStage.REVOKED},
    ModuleStage.SUSPENDED: {ModuleStage.ENABLED_READONLY, ModuleStage.REVOKED},
    ModuleStage.REVOKED: set(),
}


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    version: str
    digest: str
    source_commit: str | None
    signer: str | None
    sbom_digest: str | None
    risk: RiskClass
    required_tools: tuple[str, ...] = ()
    network_permissions: tuple[str, ...] = ()
    filesystem_permissions: tuple[str, ...] = ()
    child_skills: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillState:
    manifest: SkillManifest
    stage: ModuleStage = ModuleStage.DISCOVERED

    def transition(self, target: ModuleStage) -> Self:
        if target not in _ALLOWED[self.stage]:
            raise ValueError(f"invalid skill transition: {self.stage} -> {target}")
        return SkillState(self.manifest, target)
