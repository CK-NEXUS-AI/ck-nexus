from creator_app.agnes.fabric import AGNESCapabilityFabric, ModuleCatalog
from creator_app.agnes.fabric.memory import choose_memory_tier
from creator_app.agnes.fabric.models import ModuleStage, ResourceSnapshot, RiskClass
from creator_app.agnes.fabric.quality import select_runtime_decision
from creator_app.agnes.fabric.skills import SkillManifest, SkillState


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


def test_dependency_plan_is_declarative_only():
    plan = AGNESCapabilityFabric().external_dependency_plan()
    assert "docling" in plan["python_packages"]
    assert "ffmpeg" in plan["host_binaries"]
    assert "opa" in plan["host_binaries"]
