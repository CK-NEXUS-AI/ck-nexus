from __future__ import annotations

import hashlib
import json
from typing import Any


class DeterministicState:
    """Canonical state hashing and deterministic choice without mutable RNG state."""

    def __init__(self, *, seed: int) -> None:
        self.seed = seed

    @staticmethod
    def canonical_json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)

    def digest(self, value: Any) -> str:
        encoded = self.canonical_json({"seed": self.seed, "value": value}).encode()
        return hashlib.sha256(encoded).hexdigest()

    def choice(self, *, key: str, options: list[Any]) -> Any:
        if not options:
            raise ValueError("deterministic choice requires at least one option")
        material = f"{self.seed}:{key}".encode()
        index = int.from_bytes(hashlib.sha256(material).digest()[:8], "big") % len(options)
        return options[index]

    def verify_same_input_same_digest(self, value: Any) -> bool:
        return self.digest(value) == self.digest(value)
