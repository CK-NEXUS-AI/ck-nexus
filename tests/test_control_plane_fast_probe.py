import asyncio

from creator_app.control_plane.fast_probe import FastProbeRunner


def test_independent_probes_run_concurrently() -> None:
    active = 0
    peak = 0

    async def probe(name: str) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.03)
        active -= 1
        return name

    async def run() -> object:
        return await FastProbeRunner().run(
            {"a": lambda: probe("a"), "b": lambda: probe("b"), "c": lambda: probe("c")}
        )

    results = asyncio.run(run())
    assert peak == 2
    assert {key: value.status for key, value in results.items()} == {
        "a": "ok",
        "b": "ok",
        "c": "ok",
    }


def test_failing_probe_does_not_block_unrelated_probe() -> None:
    async def bad() -> str:
        raise RuntimeError("sensitive internal detail")

    async def good() -> str:
        return "ok"

    async def run() -> object:
        return await FastProbeRunner().run({"bad": bad, "good": good})

    results = asyncio.run(run())
    assert results["bad"].status == "error"
    assert results["bad"].error == "RuntimeError"
    assert results["good"].status == "ok"


def test_empty_probe_set_returns_immediately() -> None:
    assert asyncio.run(FastProbeRunner().run({})) == {}
