from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryModuleState(StrEnum):
    BLOCKED = "blocked"
    INSTALLED_DISABLED = "installed_disabled"
    ENABLED = "enabled"


class CognitiveMemoryManifest(BaseModel):
    module_id: str = "ck-nexus.gen6-3.memory-learning"
    module_version: str = "0.1.0-dev"
    schema_version: int = 1
    required_runtime_contract: str = "gen6.2"
    provider_sdk_required: bool = False
    production_mutation_allowed: bool = False
    auto_enable_after_install: bool = False
    components: tuple[str, ...] = (
        "memory_decay",
        "dream_consolidator",
        "experience_skill",
        "memory_benchmarks",
    )


class MemoryModuleActivationInput(BaseModel):
    runtime_contract: str = Field(min_length=1)
    exact_subject: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()
    ci_verified: bool = False
    independent_verification: bool = False
    governor_approved: bool = False


class MemoryModuleActivationResult(BaseModel):
    compatible: bool
    state: MemoryModuleState
    reasons: tuple[str, ...] = ()
    production_activation_allowed: bool = False


class CognitiveMemoryModuleGate:
    """Fail-closed install/enable gate for the reconciled Gen 6.3 module."""

    def __init__(self, manifest: CognitiveMemoryManifest | None = None) -> None:
        self.manifest = manifest or CognitiveMemoryManifest()

    def check_install(
        self,
        request: MemoryModuleActivationInput,
    ) -> MemoryModuleActivationResult:
        reasons: list[str] = []
        if request.runtime_contract != self.manifest.required_runtime_contract:
            reasons.append("runtime_contract_incompatible")
        if not request.exact_subject.strip():
            reasons.append("exact_subject_missing")
        if not request.evidence_ids:
            reasons.append("evidence_missing")
        if not request.ci_verified:
            reasons.append("ci_not_verified")
        if not request.independent_verification:
            reasons.append("independent_verification_missing")
        compatible = not reasons
        return MemoryModuleActivationResult(
            compatible=compatible,
            state=(
                MemoryModuleState.INSTALLED_DISABLED
                if compatible
                else MemoryModuleState.BLOCKED
            ),
            reasons=tuple(reasons),
            production_activation_allowed=False,
        )

    def check_enable(
        self,
        request: MemoryModuleActivationInput,
    ) -> MemoryModuleActivationResult:
        install = self.check_install(request)
        reasons = list(install.reasons)
        if not request.governor_approved:
            reasons.append("ck_governor_approval_required")
        compatible = not reasons
        return MemoryModuleActivationResult(
            compatible=compatible,
            state=MemoryModuleState.ENABLED if compatible else MemoryModuleState.BLOCKED,
            reasons=tuple(reasons),
            production_activation_allowed=False,
        )
