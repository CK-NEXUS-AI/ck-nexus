from __future__ import annotations

from dataclasses import dataclass

from creator_app.agnes_ledger import AppendOnlyLedger

from .gap_analysis import GapDecision, SubjectGapAnalyzer
from .subject import VerificationSubject


@dataclass(frozen=True, slots=True)
class ShadowObservation:
    decision: GapDecision
    ledger_sequence: int
    record_hash: str


class VerifierShadowController:
    """Record fail-closed Verifier Pro subject decisions without execution authority.

    This controller observes subject/evidence state, delegates reuse/rerun logic to
    SubjectGapAnalyzer, and appends the decision to the existing CK-NEXUS hash-chain
    ledger. It does not execute tests, write patches, issue VERIFIED, or mutate
    production state.
    """

    EVENT_TYPE = "VERIFIER_SUBJECT_GAP_DECISION"

    def __init__(
        self,
        ledger: AppendOnlyLedger,
        analyzer: SubjectGapAnalyzer | None = None,
    ) -> None:
        self.ledger = ledger
        self.analyzer = analyzer or SubjectGapAnalyzer()

    def observe(
        self,
        *,
        current: VerificationSubject,
        previous: VerificationSubject | None,
        evidence_complete: bool,
        evidence_fresh: bool,
        verifier_separation_valid: bool,
    ) -> ShadowObservation:
        ledger_state = self.ledger.verify()
        decision = self.analyzer.assess(
            current=current,
            previous=previous,
            ledger_valid=ledger_state.valid,
            evidence_complete=evidence_complete,
            evidence_fresh=evidence_fresh,
            verifier_separation_valid=verifier_separation_valid,
        )

        if not ledger_state.valid:
            raise RuntimeError(
                "refusing to append verifier decision to an invalid evidence ledger"
            )

        payload = {
            "schema_version": "1.0",
            "subject_id": decision.current_subject_id,
            "subject_digest": decision.current_subject_digest,
            "previous_subject_id": previous.subject_id if previous is not None else None,
            "previous_subject_digest": previous.digest if previous is not None else None,
            "status": decision.status.value,
            "changed_components": [item.value for item in decision.changed_components],
            "rerun_scopes": [item.value for item in decision.rerun_scopes],
            "authoritative_reuse_allowed": decision.authoritative_reuse_allowed,
            "historical_reference_allowed": decision.historical_reference_allowed,
            "reasons": list(decision.reasons),
            "production_mutation": False,
            "verification_authority": False,
        }
        record = self.ledger.append(self.EVENT_TYPE, payload)
        return ShadowObservation(
            decision=decision,
            ledger_sequence=int(record["sequence"]),
            record_hash=str(record["hash"]),
        )
