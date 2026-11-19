import asyncio

from creator_app.control_plane.orchestrator import ControlPlaneOrchestrator


def test_known_signal_uses_fast_path_without_ai_diagnosis() -> None:
    orchestrator = ControlPlaneOrchestrator()
    decision = orchestrator.fast_path("cknexus-mcp.service inactive")
    assert decision.handled is True
    assert decision.action_id == "restart_cknexus_mcp"


def test_unknown_signal_remains_unhandled_for_diagnosis() -> None:
    orchestrator = ControlPlaneOrchestrator()
    decision = orchestrator.fast_path("unknown failure")
    assert decision.handled is False
    assert decision.action_id is None


def test_fast_probe_is_bounded_and_health_cache_avoids_duplicate_probe() -> None:
    orchestrator = ControlPlaneOrchestrator()
    calls = 0

    async def probe() -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.01)
        return "healthy"

    async def run() -> object:
        first = await orchestrator.health_cached("gateway", probe)
        second = await orchestrator.health_cached("gateway", probe)
        return first, second

    first, second = asyncio.run(run())
    assert first.status == "ok"
    assert second.status == "ok"
    assert calls == 1
