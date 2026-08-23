from creator_app.agnes.polyglot.equivalence import verify_equivalence
from creator_app.agnes.polyglot.semantic_ir import Contract, SemanticIR, Symbol
from creator_app.agnes.polyglot.toolchain_registry import (
    LanguageToolchain,
    ToolSpec,
    ToolchainRegistry,
    ToolchainStatus,
)


def test_semantic_ir_validation_and_contract_projection() -> None:
    ir = SemanticIR(
        intent="preserve addition behavior",
        source_language="python",
        symbols=[Symbol("x", "int"), Symbol("y", "int")],
        contracts=[Contract("sum", "result == x + y", "postcondition")],
        security_invariants=["no external side effects"],
    )
    assert ir.validate() == []
    contract = ir.observable_contract()
    assert contract["intent"] == "preserve addition behavior"
    assert contract["contracts"][0]["name"] == "sum"


def test_equivalence_requires_cases_and_contracts() -> None:
    ok = verify_equivalence(
        [("one", 3, 3), ("two", {"a": 1}, {"a": 1})],
        contract_checks={"postcondition": True},
    )
    assert ok.status == "VERIFIED"

    mismatch = verify_equivalence([("one", 3, 4)])
    assert mismatch.status == "NOT_VERIFIED"

    no_cases = verify_equivalence([])
    assert no_cases.status == "NOT_VERIFIED"


def test_toolchain_registry_missing_unknown_language() -> None:
    registry = ToolchainRegistry()
    assert registry.probe("unknown") is ToolchainStatus.MISSING


def test_toolchain_registry_probes_required_commands() -> None:
    registry = ToolchainRegistry()
    registry.register(LanguageToolchain("testlang", [ToolSpec("python", "python", "runtime")]))
    assert registry.probe("testlang") in {ToolchainStatus.AVAILABLE, ToolchainStatus.MISSING}
    snap = registry.snapshot()["testlang"]
    assert snap["tools"][0]["role"] == "runtime"
