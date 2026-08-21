from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ModuleState(StrEnum):
    AVAILABLE = "available"
    BLOCKED = "blocked"
    INSTALLED_DISABLED = "installed_disabled"
    ENABLED = "enabled"


class CognitiveMemoryManifest(BaseModel):
    module_id: str = "ck-nexus.gen6-3.cognitive-memory"
    module_version: str = "0.1.0-dev"
    schema_version: int = 1
    required_runtime_contract: str = "gen6.2"
    provider_sdk_required: bool = False
    production_mutation_allowed: bool = False
    auto_enable_after_install: bool = False
    components: tuple[str, ...] = (
        "memory_decay",
        "dream_consolidation",
        "experience_skill",
        "memory_regression",
    )


class ModuleCompatibilityInput(BaseModel):
    runtime_contract: str = Field(min_length=1)
    evidence_verified: bool = False
    ci_verified: bool = False
    governor_approved: bool = False


class ModuleCompatibilityResult(BaseModel):
    compatible: bool
    state: ModuleState
    reasons: list[str] = Field(default_factory=list)


class CognitiveMemoryModuleGate:
    """Fail-closed gate for installing and enabling the Gen 6.3 module."""

    def __init__(self, manifest: CognitiveMemoryManifest | None = None) -> None:
        self.manifest = manifest or CognitiveMemoryManifest()

    def check_install(
        self,
        request: ModuleCompatibilityInput,
    ) -> ModuleCompatibilityResult:
        reasons: list[str] = []
        if request.runtime_contract != self.manifest.required_runtime_contract:
            reasons.append("runtime contract is incompatible")
        if not request.ci_verified:
            reasons.append("CI evidence is not verified")
        if not request.evidence_verified:
            reasons.append("module evidence is not verified")

        compatible = not reasons
        return ModuleCompatibilityResult(
            compatible=compatible,
            state=(
                ModuleState.INSTALLED_DISABLED
                if compatible
                else ModuleState.BLOCKED
            ),
            reasons=reasons,
        )

    def check_enable(
        self,
        request: ModuleCompatibilityInput,
    ) -> ModuleCompatibilityResult:
        install = self.check_install(request)
        reasons = list(install.reasons)
        if not request.governor_approved:
            reasons.append("CK Governor approval is required")

        compatible = not reasons
        return ModuleCompatibilityResult(
            compatible=compatible,
            state=ModuleState.ENABLED if compatible else ModuleState.BLOCKED,
            reasons=reasons,
        )
