import subprocess
import sys

import pytest

from creator_app.agnes.fabric import AGNESCapabilityFabric, ModuleCatalog
from creator_app.agnes.fabric.memory import choose_memory_tier
from creator_app.agnes.fabric.models import ModuleStage, ResourceSnapshot, RiskClass
from creator_app.agnes.fabric.quality import select_runtime_decision
from creator_app.agnes.fabric.resource import snapshot
from creator_app.agnes.fabric.skills import SkillManifest, SkillState, TransitionReceipt


def resource(*, available=4_000_000_000, psi=0.0, thermal=40.0):
    return ResourceSnapshot(
        total_ram_bytes=8_000_000_000,
        available_ram_bytes=available,
        load_1m=0.1,
        memory_psi_avg10=psi,
        cpu_psi_avg10=0.0,
        io_psi_avg10=0.0,
        thermal_celsius=thermal,
        zram_present=False,
        writable_cgroup_v2=False,
        cgroup_v2_present=False,
    )


def test_catalog_installs_all_major_domains():
    catalog = ModuleCatalog()
    ids = {module.module_id for module in catalog.all()}
    expected = {
        "research.intelligence",
        "protocol.mcp",
        "protocol.a2a",
        "memory.agent",
        "resource.ram",
        "quality.color",
        "quality.visual_verify",
        "edge.runtime",
        "supply.sbom",
        "evidence.graph",
        "claims.compiler",
        "self_improvement.lab",
    }
    assert expected <= ids
    assert len(ids) >= 45


def test_self_improvement_is_disabled_by_default():
    module = ModuleCatalog().get("self_improvement.lab")
    assert module.write_capable is True
    assert module.risk is RiskClass.R4_CRITICAL
    assert module.default_mode.value == "DISABLED"


def test_memory_policy_moves_cold_under_pressure():
    assert choose_memory_tier(resource(psi=25.0), 1_000_000) == "COLD"


def test_quality_policy_downgrades_under_thermal_pressure():
    decision = select_runtime_decision(resource(thermal=75.0))
    assert decision.quality_profile == "ECO"
    assert decision.max_concurrency == 1


def test_quality_policy_can_choose_quality_with_headroom():
    decision = select_runtime_decision(resource(available=10_000_000_000, psi=0.1))
    assert decision.quality_profile == "QUALITY"


def test_missing_resource_evidence_fails_to_lowest_concurrency():
    decision = select_runtime_decision(resource(available=None, psi=None, thermal=None))
    assert decision.quality_profile == "ECO"
    assert decision.memory_tier == "COLD"
    assert decision.max_concurrency == 1
    assert set(decision.reason_codes) == {
        "MISSING_MEMORY_PSI",
        "MISSING_AVAILABLE_RAM",
        "MISSING_THERMAL",
    }


def test_memory_policy_rejects_nonpositive_item_size():
    with pytest.raises(ValueError):
        choose_memory_tier(resource(), 0)


def test_read_only_snapshot_never_claims_cgroup_enforcement():
    assert snapshot().writable_cgroup_v2 is False


def test_skill_cannot_skip_security_lifecycle():
    state = SkillState(
        SkillManifest(
            skill_id="demo",
            version="1",
            digest="sha256:demo",
            source_commit=None,
            signer=None,
            sbom_digest=None,
            risk=RiskClass.R0_READ,
        )
    )
    try:
        state.transition(ModuleStage.APPROVED_READWRITE)
    except ValueError:
        pass
    else:
        raise AssertionError("skill lifecycle allowed an approval bypass")


def test_skill_privilege_increase_requires_digest_bound_evidence():
    digest = "sha256:" + "a" * 64
    policy_digest = "sha256:" + "b" * 64
    state = SkillState(
        SkillManifest(
            skill_id="governed-demo",
            version="1",
            digest=digest,
            source_commit="0123456789abcdef",
            signer="release-authority",
            sbom_digest="sha256:" + "c" * 64,
            risk=RiskClass.R2_REVERSIBLE_WRITE,
            write_capable=True,
        )
    )

    with pytest.raises(ValueError, match="requires evidence"):
        state.transition(ModuleStage.INSPECTED)

    for index, stage in enumerate(
        (
            ModuleStage.INSPECTED,
            ModuleStage.SCANNED,
            ModuleStage.EVALUATED,
            ModuleStage.APPROVED,
            ModuleStage.ENABLED_READONLY,
            ModuleStage.APPROVED_READWRITE,
        ),
        start=1,
    ):
        state = state.transition(
            stage,
            receipt=TransitionReceipt(
                stage=stage,
                subject_digest=digest,
                evidence_digest="sha256:" + f"{index:x}" * 64,
                actor_id="ck-governor",
                policy_digest=policy_digest if stage in {
                    ModuleStage.APPROVED,
                    ModuleStage.APPROVED_READWRITE,
                } else None,
            ),
        )

    assert state.stage is ModuleStage.APPROVED_READWRITE
    assert len(state.receipts) == 6


def test_r4_skill_cannot_use_generic_readwrite_transition():
    digest = "sha256:" + "d" * 64
    state = SkillState(
        SkillManifest(
            skill_id="critical-demo",
            version="1",
            digest=digest,
            source_commit="0123456789abcdef",
            signer="release-authority",
            sbom_digest="sha256:" + "e" * 64,
            risk=RiskClass.R4_CRITICAL,
            write_capable=True,
        )
    )
    stages = (
        ModuleStage.INSPECTED,
        ModuleStage.SCANNED,
        ModuleStage.EVALUATED,
        ModuleStage.APPROVED,
        ModuleStage.ENABLED_READONLY,
    )
    for index, stage in enumerate(stages, start=1):
        state = state.transition(
            stage,
            receipt=TransitionReceipt(
                stage=stage,
                subject_digest=digest,
                evidence_digest="sha256:" + f"{index:x}" * 64,
                actor_id="ck-governor",
                policy_digest="sha256:" + "f" * 64 if stage is ModuleStage.APPROVED else None,
            ),
        )

    with pytest.raises(ValueError, match="separate critical-action authority"):
        state.transition(
            ModuleStage.APPROVED_READWRITE,
            receipt=TransitionReceipt(
                stage=ModuleStage.APPROVED_READWRITE,
                subject_digest=digest,
                evidence_digest="sha256:" + "9" * 64,
                actor_id="ck-governor",
                policy_digest="sha256:" + "f" * 64,
            ),
        )


def test_dependency_plan_is_declarative_only():
    plan = AGNESCapabilityFabric().external_dependency_plan()
    assert "docling" in plan["python_packages"]
    assert "ffmpeg" in plan["host_binaries"]
    assert "opa" in plan["host_binaries"]


def test_bootstrap_rejects_removed_host_mutation_flag():
    result = subprocess.run(
        [sys.executable, "scripts/agnes_module_bootstrap.py", "--apply-python"],
        capture_output=True,
        check=False,
        text=True,
    )
    assert result.returncode == 2
    assert "unrecognized arguments: --apply-python" in result.stderr
