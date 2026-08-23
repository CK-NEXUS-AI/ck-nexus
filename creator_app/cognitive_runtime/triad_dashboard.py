from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import Any

from .triad_learning import LearningLedgerSnapshot, TriadLearningConsolidator
from .triad_pulse import PulseKind, TriadPulseEngine, TriadPulseSnapshot


class TriadDashboardError(ValueError):
    """Raised when dashboard projection provenance cannot be trusted."""


class TriadDashboardProjector:
    """Read-only public projection for the AGNES Triad development pipeline.

    The projector exposes bounded operational state and digests only. It never
    exposes receipt payloads, hidden reasoning, credentials, or mutation paths.
    """

    SCHEMA_VERSION = "1.0"
    TRUTH_STATE = "MEASURED_NOT_VERIFIED"
    AUTHORITY = "READ_ONLY_PROJECTION"

    def __init__(self, subject_sha: str) -> None:
        if not subject_sha.strip():
            raise TriadDashboardError("subject_sha_required")
        self.subject_sha = subject_sha

    @staticmethod
    def _require_digest(value: str, field: str) -> None:
        if len(value) != 64:
            raise TriadDashboardError(f"{field}_invalid")
        try:
            int(value, 16)
        except ValueError as exc:
            raise TriadDashboardError(f"{field}_invalid") from exc

    @staticmethod
    def digest(projection: dict[str, Any]) -> str:
        public = deepcopy(projection)
        public.pop("projection_digest", None)
        raw = json.dumps(public, sort_keys=True, separators=(",", ":"))
        return sha256(raw.encode("utf-8")).hexdigest()

    def project(
        self,
        *,
        pulse_snapshot: TriadPulseSnapshot,
        expected_pulse_head_digest: str,
        learning_snapshot: LearningLedgerSnapshot,
        expected_learning_head_digest: str,
    ) -> dict[str, Any]:
        TriadPulseEngine.verify_snapshot(
            pulse_snapshot,
            expected_subject_sha=self.subject_sha,
            expected_head_digest=expected_pulse_head_digest,
        )
        TriadLearningConsolidator.verify_ledger_snapshot(
            learning_snapshot,
            expected_subject_sha=self.subject_sha,
            expected_head_digest=expected_learning_head_digest,
        )

        pulse_by_id = {pulse.pulse_id: pulse for pulse in pulse_snapshot.pulses}
        for record in learning_snapshot.records:
            source = pulse_by_id.get(record.source_pulse_id)
            if source is None:
                raise TriadDashboardError("learning_source_pulse_missing")
            if source.kind is not PulseKind.CONSOLIDATE_20:
                raise TriadDashboardError("learning_source_pulse_invalid")
            self._require_digest(record.candidate_digest, "learning_candidate_digest")
            self._require_digest(record.semantic_fingerprint, "learning_fingerprint")

        review_pulses = tuple(
            pulse
            for pulse in pulse_snapshot.pulses
            if pulse.kind is PulseKind.REVIEW_15
        )
        consolidation_pulses = tuple(
            pulse
            for pulse in pulse_snapshot.pulses
            if pulse.kind is PulseKind.CONSOLIDATE_20
        )
        latest = pulse_snapshot.pulses[-1] if pulse_snapshot.pulses else None
        latest_consolidation = consolidation_pulses[-1] if consolidation_pulses else None

        learning_records = [
            {
                "sequence": record.sequence,
                "learning_id": record.learning_id,
                "candidate_digest": record.candidate_digest,
                "semantic_fingerprint": record.semantic_fingerprint,
                "source_pulse_id": record.source_pulse_id,
                "supersedes_learning_id": record.supersedes_learning_id,
                "record_digest": record.record_digest,
            }
            for record in learning_snapshot.records
        ]

        projection: dict[str, Any] = {
            "schema_version": self.SCHEMA_VERSION,
            "subject_sha": self.subject_sha,
            "authority": self.AUTHORITY,
            "truth_state": self.TRUTH_STATE,
            "independent_verification_required": True,
            "verified_claim_allowed": False,
            "mutation_allowed": False,
            "external_action_allowed": False,
            "production_mutation_allowed": False,
            "source_heads": {
                "pulse": pulse_snapshot.head_digest,
                "learning": learning_snapshot.head_digest,
            },
            "pipeline": {
                "pulse": {
                    "receipt_count": len(pulse_snapshot.records),
                    "pulse_count": len(pulse_snapshot.pulses),
                    "review_15_count": len(review_pulses),
                    "consolidate_20_count": len(consolidation_pulses),
                    "latest": (
                        {
                            "pulse_id": latest.pulse_id,
                            "kind": latest.kind.value,
                            "ordinal": latest.ordinal,
                            "window_start": latest.window_start,
                            "window_end": latest.window_end,
                            "window_digest": latest.window_digest,
                            "measured_count": latest.measured_count,
                            "blocked_count": latest.blocked_count,
                            "contradicted_count": latest.contradicted_count,
                            "rejected_count": latest.rejected_count,
                            "mean_score_bps": latest.mean_score_bps,
                            "measured_ratio_bps": latest.measured_ratio_bps,
                        }
                        if latest is not None
                        else None
                    ),
                },
                "learning": {
                    "proposal_count": len(learning_records),
                    "ledger_head_digest": learning_snapshot.head_digest,
                    "latest_source_pulse_id": (
                        latest_consolidation.pulse_id
                        if latest_consolidation is not None
                        else None
                    ),
                    "records": learning_records,
                    "adoption_allowed": False,
                    "auto_activation_allowed": False,
                },
            },
            "privacy": {
                "receipt_payloads_exposed": False,
                "hidden_reasoning_exposed": False,
                "credential_material_exposed": False,
            },
        }
        projection["projection_digest"] = self.digest(projection)
        return projection

    def verify_projection(self, projection: dict[str, Any]) -> None:
        if projection.get("schema_version") != self.SCHEMA_VERSION:
            raise TriadDashboardError("projection_schema_invalid")
        if projection.get("subject_sha") != self.subject_sha:
            raise TriadDashboardError("projection_subject_mismatch")
        if projection.get("authority") != self.AUTHORITY:
            raise TriadDashboardError("projection_authority_invalid")
        if projection.get("truth_state") != self.TRUTH_STATE:
            raise TriadDashboardError("projection_truth_invalid")
        if projection.get("verified_claim_allowed") is not False:
            raise TriadDashboardError("projection_verified_claim_forbidden")
        for flag in (
            "mutation_allowed",
            "external_action_allowed",
            "production_mutation_allowed",
        ):
            if projection.get(flag) is not False:
                raise TriadDashboardError(f"projection_{flag}_forbidden")
        privacy = projection.get("privacy")
        if not isinstance(privacy, dict):
            raise TriadDashboardError("projection_privacy_missing")
        if any(privacy.get(key) is not False for key in (
            "receipt_payloads_exposed",
            "hidden_reasoning_exposed",
            "credential_material_exposed",
        )):
            raise TriadDashboardError("projection_privacy_boundary_invalid")
        claimed = projection.get("projection_digest")
        if not isinstance(claimed, str):
            raise TriadDashboardError("projection_digest_missing")
        self._require_digest(claimed, "projection_digest")
        if claimed != self.digest(projection):
            raise TriadDashboardError("projection_digest_mismatch")
