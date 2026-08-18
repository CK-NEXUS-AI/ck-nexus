"""Evidence-bound skill lifecycle and supply-chain contract.

This module validates ordered, digest-bound transition receipts. Cryptographic
signature and policy verification remain external runtime responsibilities.
"""

from dataclasses import dataclass
from string import hexdigits
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

_PRIVILEGE_INCREASING = {
    ModuleStage.INSPECTED,
    ModuleStage.SCANNED,
    ModuleStage.EVALUATED,
    ModuleStage.APPROVED,
    ModuleStage.ENABLED_READONLY,
    ModuleStage.APPROVED_READWRITE,
}


def _is_sha256(value: str | None) -> bool:
    if value is None or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in hexdigits for character in digest)


@dataclass(frozen=True)
class SkillManifest:
    skill_id: str
    version: str
    digest: str
    source_commit: str | None
    signer: str | None
    sbom_digest: str | None
    risk: RiskClass
    write_capable: bool = False
    required_tools: tuple[str, ...] = ()
    network_permissions: tuple[str, ...] = ()
    filesystem_permissions: tuple[str, ...] = ()
    child_skills: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransitionReceipt:
    stage: ModuleStage
    subject_digest: str
    evidence_digest: str
    actor_id: str
    policy_digest: str | None = None


def _validate_receipt(
    manifest: SkillManifest,
    target: ModuleStage,
    receipt: TransitionReceipt,
) -> None:
    if receipt.stage is not target:
        raise ValueError("transition receipt stage does not match target")
    if receipt.subject_digest != manifest.digest or not _is_sha256(receipt.subject_digest):
        raise ValueError("transition receipt is not bound to a valid manifest digest")
    if not _is_sha256(receipt.evidence_digest):
        raise ValueError("transition receipt requires a sha256 evidence digest")
    if not receipt.actor_id.strip():
        raise ValueError("transition receipt requires an actor_id")
    if target in {ModuleStage.APPROVED, ModuleStage.APPROVED_READWRITE} and not _is_sha256(
        receipt.policy_digest
    ):
        raise ValueError("approval transition requires a sha256 policy digest")
    if target is ModuleStage.APPROVED_READWRITE:
        if not manifest.write_capable:
            raise ValueError("read/write approval requires a write-capable manifest")
        if manifest.risk is RiskClass.R4_CRITICAL:
            raise ValueError("R4 skills require a separate critical-action authority")
        provenance_ready = (
            manifest.source_commit
            and manifest.signer
            and _is_sha256(manifest.sbom_digest)
        )
        if not provenance_ready:
            raise ValueError("read/write approval requires source, signer and SBOM provenance")


@dataclass(frozen=True, init=False)
class SkillState:
    manifest: SkillManifest
    stage: ModuleStage
    receipts: tuple[TransitionReceipt, ...]

    def __init__(self, manifest: SkillManifest) -> None:
        object.__setattr__(self, "manifest", manifest)
        object.__setattr__(self, "stage", ModuleStage.DISCOVERED)
        object.__setattr__(self, "receipts", ())

    @classmethod
    def _from_transition(
        cls,
        state: Self,
        target: ModuleStage,
        receipt: TransitionReceipt | None,
    ) -> Self:
        result = object.__new__(cls)
        object.__setattr__(result, "manifest", state.manifest)
        object.__setattr__(result, "stage", target)
        receipts = state.receipts + ((receipt,) if receipt is not None else ())
        object.__setattr__(result, "receipts", receipts)
        return result

    def transition(
        self,
        target: ModuleStage,
        *,
        receipt: TransitionReceipt | None = None,
    ) -> Self:
        if target not in _ALLOWED[self.stage]:
            raise ValueError(f"invalid skill transition: {self.stage} -> {target}")
        if target in _PRIVILEGE_INCREASING:
            if receipt is None:
                raise ValueError("privilege-increasing transition requires evidence")
            _validate_receipt(self.manifest, target, receipt)
        elif receipt is not None:
            _validate_receipt(self.manifest, target, receipt)
        return self._from_transition(self, target, receipt)
