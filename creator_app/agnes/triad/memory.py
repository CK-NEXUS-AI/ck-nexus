from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any


class MemoryLayer(str, Enum):
    WORKING = "WORKING"
    DIALOGUE = "DIALOGUE"
    DISCOVERED = "DISCOVERED"
    CANDIDATE = "CANDIDATE"
    MEASURED = "MEASURED"
    VERIFIED = "VERIFIED"
    FAILURE = "FAILURE"


_ALLOWED_TRANSITIONS: dict[MemoryLayer, set[MemoryLayer]] = {
    MemoryLayer.WORKING: {MemoryLayer.DIALOGUE, MemoryLayer.DISCOVERED, MemoryLayer.FAILURE},
    MemoryLayer.DIALOGUE: {MemoryLayer.DISCOVERED, MemoryLayer.CANDIDATE, MemoryLayer.FAILURE},
    MemoryLayer.DISCOVERED: {MemoryLayer.CANDIDATE, MemoryLayer.FAILURE},
    MemoryLayer.CANDIDATE: {MemoryLayer.MEASURED, MemoryLayer.FAILURE},
    MemoryLayer.MEASURED: {MemoryLayer.VERIFIED, MemoryLayer.FAILURE},
    MemoryLayer.VERIFIED: set(),
    MemoryLayer.FAILURE: set(),
}


@dataclass(slots=True)
class TriadMemoryEntry:
    entry_id: str
    cycle_id: str
    producer_id: str
    content: dict[str, Any]
    layer: MemoryLayer
    evidence_refs: list[str] = field(default_factory=list)
    verifier_id: str | None = None
    verification_evidence_digest: str | None = None

    @classmethod
    def create(
        cls,
        *,
        cycle_id: str,
        producer_id: str,
        content: dict[str, Any],
        layer: MemoryLayer = MemoryLayer.WORKING,
    ) -> "TriadMemoryEntry":
        body = {
            "cycle_id": cycle_id,
            "producer_id": producer_id,
            "content": content,
            "layer": layer.value,
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return cls(
            entry_id=hashlib.sha256(raw.encode()).hexdigest(),
            cycle_id=cycle_id,
            producer_id=producer_id,
            content=dict(content),
            layer=layer,
        )

    def promote(self, target: MemoryLayer, *, evidence_refs: list[str] | None = None) -> None:
        if target not in _ALLOWED_TRANSITIONS[self.layer]:
            raise ValueError(f"invalid memory transition {self.layer} -> {target}")
        if target is MemoryLayer.MEASURED and not evidence_refs:
            raise ValueError("MEASURED requires evidence refs")
        if target is MemoryLayer.VERIFIED:
            raise ValueError("use attach_independent_verification for VERIFIED")
        if evidence_refs:
            self.evidence_refs.extend(ref for ref in evidence_refs if ref not in self.evidence_refs)
        self.layer = target

    def attach_independent_verification(self, verifier_id: str, evidence_digest: str) -> None:
        if self.layer is not MemoryLayer.MEASURED:
            raise ValueError("memory must be MEASURED before verification")
        if verifier_id == self.producer_id:
            raise ValueError("self-verification is forbidden")
        if not evidence_digest:
            raise ValueError("verification evidence digest is required")
        self.verifier_id = verifier_id
        self.verification_evidence_digest = evidence_digest
        self.layer = MemoryLayer.VERIFIED

    def reject(self, evidence_ref: str) -> None:
        if evidence_ref and evidence_ref not in self.evidence_refs:
            self.evidence_refs.append(evidence_ref)
        self.layer = MemoryLayer.FAILURE


@dataclass(slots=True)
class TriadMemoryStore:
    entries: dict[str, TriadMemoryEntry] = field(default_factory=dict)

    def put(self, entry: TriadMemoryEntry) -> None:
        self.entries.setdefault(entry.entry_id, entry)

    def by_layer(self, layer: MemoryLayer) -> tuple[TriadMemoryEntry, ...]:
        return tuple(entry for entry in self.entries.values() if entry.layer is layer)

    def by_cycle(self, cycle_id: str) -> tuple[TriadMemoryEntry, ...]:
        return tuple(entry for entry in self.entries.values() if entry.cycle_id == cycle_id)
