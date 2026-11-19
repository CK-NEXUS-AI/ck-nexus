"""Bounded verification and repair gate for control-plane results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VerificationResult:
    state: str
    attempts: int
    evidence_refs: tuple[str, ...]
    release_evidence: bool
    patch_applied: bool = False


class ControlPlaneVerifier:
    """Require verification before release evidence and never apply patches."""

    def __init__(self, *, max_repairs: int = 2) -> None:
        if max_repairs < 0 or max_repairs > 5:
            raise ValueError("max_repairs must be between 0 and 5")
        self.max_repairs = max_repairs

    def evaluate(
        self,
        *,
        state: str,
        test_ok: bool,
        security_ok: bool,
        evidence_refs: Sequence[str],
    ) -> VerificationResult:
        refs = tuple(evidence_refs)
        evidence_valid = bool(refs) and all(
            isinstance(ref, str) and bool(ref.strip()) for ref in refs
        )
        verified = (
            state == "EXECUTED_UNVERIFIED" and test_ok and security_ok and evidence_valid
        )
        return VerificationResult(
            state="VERIFIED" if verified else "FAILED",
            attempts=1,
            evidence_refs=refs,
            release_evidence=verified,
            patch_applied=False,
        )

    def repair_loop(
        self,
        *,
        verify: Callable[[int], bool],
        evidence_refs: Sequence[str],
    ) -> VerificationResult:
        refs = tuple(evidence_refs)
        evidence_valid = bool(refs) and all(
            isinstance(ref, str) and bool(ref.strip()) for ref in refs
        )
        if not evidence_valid:
            return VerificationResult(
                state="FAILED",
                attempts=0,
                evidence_refs=refs,
                release_evidence=False,
                patch_applied=False,
            )

        attempts = 0
        for attempt in range(1, self.max_repairs + 2):
            attempts = attempt
            try:
                verified = verify(attempt)
            except Exception:
                # Verification infrastructure failures are not proof of success.
                # Continue only within the configured bounded retry budget.
                continue
            if verified:
                return VerificationResult(
                    state="VERIFIED",
                    attempts=attempt,
                    evidence_refs=refs,
                    release_evidence=True,
                    patch_applied=False,
                )
        return VerificationResult(
            state="FAILED",
            attempts=attempts,
            evidence_refs=refs,
            release_evidence=False,
            patch_applied=False,
        )
