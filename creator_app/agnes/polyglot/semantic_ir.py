"""Language-neutral semantic intermediate representation.

This module models meaning and observable behavior rather than syntax. It is
intentionally conservative: it stores declared semantics but does not claim
behavioral equivalence without verifier evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Symbol:
    name: str
    type_name: str | None = None
    mutable: bool = False
    scope: str | None = None


@dataclass(frozen=True)
class SideEffect:
    kind: str
    target: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Contract:
    name: str
    expression: str
    kind: str = "invariant"


@dataclass
class SemanticIR:
    """Minimal language-neutral semantic model for polyglot transformations."""

    intent: str
    source_language: str
    symbols: list[Symbol] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    data_flow: list[tuple[str, str]] = field(default_factory=list)
    control_flow: list[str] = field(default_factory=list)
    side_effects: list[SideEffect] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)
    security_invariants: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.intent.strip():
            errors.append("intent must not be empty")
        if not self.source_language.strip():
            errors.append("source_language must not be empty")
        symbol_names = [symbol.name for symbol in self.symbols]
        if len(symbol_names) != len(set(symbol_names)):
            errors.append("symbol names must be unique")
        return errors

    def observable_contract(self) -> dict[str, Any]:
        """Return the subset that must be preserved across implementations."""
        return {
            "intent": self.intent,
            "state": self.state,
            "data_flow": list(self.data_flow),
            "control_flow": list(self.control_flow),
            "side_effects": [effect.__dict__ for effect in self.side_effects],
            "contracts": [contract.__dict__ for contract in self.contracts],
            "security_invariants": list(self.security_invariants),
        }
