from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    missing_effects: tuple[str, ...]
    unexpected_effects: tuple[str, ...]


def verify_effects(expected: tuple[str, ...], actual: tuple[str, ...]) -> VerificationResult:
    expected_set, actual_set = set(expected), set(actual)
    missing = tuple(sorted(expected_set - actual_set))
    unexpected = tuple(sorted(actual_set - expected_set))
    return VerificationResult(not missing and not unexpected, missing, unexpected)
