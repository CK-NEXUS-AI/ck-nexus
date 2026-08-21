from __future__ import annotations

import json
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any
from uuid import uuid4

from creator_app.agnes_discovery import SkillDiscoveryPolicy
from creator_app.agnes_ledger import AppendOnlyLedger


class FoundryState(StrEnum):
    DISCOVERED = "DISCOVERED"
    QUARANTINED = "QUARANTINED"
    SCANNED = "SCANNED"
    SANDBOX_TESTED = "SANDBOX_TESTED"
    BENCHMARKED = "BENCHMARKED"
    COMPATIBLE = "COMPATIBLE"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REGISTERABLE = "REGISTERABLE"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    candidate_id: str
    skill_id: str
    version: str
    source_url: str
    checksum: str
    license_id: str
    has_executable_scripts: bool
    requests_credentials: bool
    requests_network: bool
    state: FoundryState
    trust_score: float
    reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "skill_id": self.skill_id,
            "version": self.version,
            "source_url": self.source_url,
            "checksum": self.checksum,
            "license_id": self.license_id,
            "has_executable_scripts": self.has_executable_scripts,
            "requests_credentials": self.requests_credentials,
            "requests_network": self.requests_network,
            "state": self.state.value,
            "trust_score": self.trust_score,
            "reasons": list(self.reasons),
        }


class SkillFoundry:
    """Fail-closed external skill assessment pipeline.

    It never downloads, installs, activates, or promotes code. Sandbox/security
    executors submit evidence into this control plane; human approval remains separate.
    """

    def __init__(
        self, ledger: AppendOnlyLedger, discovery: SkillDiscoveryPolicy | None = None
    ) -> None:
        self.ledger = ledger
        self.discovery = discovery or SkillDiscoveryPolicy()

    def _events(self) -> list[dict[str, Any]]:
        if not self.ledger.path.exists():
            return []
        state = self.ledger.verify()
        if not state.valid:
            raise RuntimeError(f"skill foundry ledger integrity failure: {state.error}")
        rows = []
        with self.ledger.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if str(row.get("event_type", "")).startswith("skill_foundry_"):
                    rows.append(row)
        return rows

    def _state(self) -> dict[str, SkillCandidate]:
        current: dict[str, SkillCandidate] = {}
        for row in self._events():
            payload = row["payload"]
            cid = str(payload["candidate_id"])
            if row["event_type"] == "skill_foundry_discovered":
                current[cid] = SkillCandidate(
                    candidate_id=cid,
                    skill_id=str(payload["skill_id"]),
                    version=str(payload["version"]),
                    source_url=str(payload["source_url"]),
                    checksum=str(payload["checksum"]),
                    license_id=str(payload["license_id"]),
                    has_executable_scripts=bool(payload["has_executable_scripts"]),
                    requests_credentials=bool(payload["requests_credentials"]),
                    requests_network=bool(payload["requests_network"]),
                    state=FoundryState(str(payload["state"])),
                    trust_score=float(payload["trust_score"]),
                    reasons=tuple(payload.get("reasons", ())),
                )
                continue
            old = current.get(cid)
            if old is None:
                continue
            current[cid] = replace(
                old,
                state=FoundryState(str(payload["state"])),
                trust_score=float(payload.get("trust_score", old.trust_score)),
                reasons=tuple(payload.get("reasons", old.reasons)),
            )
        return current

    @staticmethod
    def _score(
        *,
        trusted_metadata: bool,
        checksum: bool,
        license_known: bool,
        security: bool = False,
        sandbox: bool = False,
        benchmark: bool = False,
        compatible: bool = False,
    ) -> float:
        score = 0.10
        score += 0.15 if trusted_metadata else 0.0
        score += 0.10 if checksum else 0.0
        score += 0.10 if license_known else 0.0
        score += 0.20 if security else 0.0
        score += 0.15 if sandbox else 0.0
        score += 0.10 if benchmark else 0.0
        score += 0.10 if compatible else 0.0
        return round(min(score, 1.0), 2)

    def discover(
        self,
        *,
        skill_id: str,
        version: str,
        source_url: str,
        checksum: str,
        license_id: str,
        has_executable_scripts: bool,
        requests_credentials: bool,
        requests_network: bool,
    ) -> SkillCandidate:
        review = self.discovery.review_candidate(
            source_url=source_url,
            checksum_present=bool(checksum.strip()),
            license_known=bool(license_id.strip()),
            has_executable_scripts=has_executable_scripts,
            requests_credentials=requests_credentials,
            requests_network=requests_network,
        )
        state = FoundryState.QUARANTINED if review.reasons else FoundryState.DISCOVERED
        cid = f"skillcand_{uuid4().hex}"
        score = self._score(
            trusted_metadata=not bool(review.reasons),
            checksum=bool(checksum.strip()),
            license_known=bool(license_id.strip()),
        )
        payload = {
            "candidate_id": cid,
            "skill_id": skill_id.strip(),
            "version": version.strip(),
            "source_url": source_url,
            "checksum": checksum.strip(),
            "license_id": license_id.strip(),
            "has_executable_scripts": has_executable_scripts,
            "requests_credentials": requests_credentials,
            "requests_network": requests_network,
            "state": state.value,
            "trust_score": score,
            "reasons": list(review.reasons),
            "auto_install": False,
            "auto_activate": False,
        }
        if not payload["skill_id"] or not payload["version"]:
            raise ValueError("skill_id and version are required")
        self.ledger.append("skill_foundry_discovered", payload)
        return self._state()[cid]

    def _transition(
        self,
        candidate_id: str,
        *,
        allowed: set[FoundryState],
        target: FoundryState,
        evidence_ref: str,
        passed: bool,
        reasons: tuple[str, ...] = (),
        score_delta: float = 0.0,
    ) -> SkillCandidate:
        state = self._state()
        candidate = state.get(candidate_id)
        if candidate is None:
            raise KeyError(candidate_id)
        if candidate.state not in allowed:
            raise RuntimeError(
                f"invalid foundry transition: {candidate.state.value} -> {target.value}"
            )
        if not evidence_ref.strip():
            raise ValueError("evidence_ref is required")
        final = target if passed else FoundryState.REJECTED
        score = round(
            min(1.0, candidate.trust_score + (score_delta if passed else 0.0)), 2
        )
        self.ledger.append(
            "skill_foundry_assessed",
            {
                "candidate_id": candidate_id,
                "state": final.value,
                "evidence_ref": evidence_ref.strip(),
                "passed": passed,
                "trust_score": score,
                "reasons": list(reasons),
            },
        )
        return self._state()[candidate_id]

    def record_security_scan(
        self,
        candidate_id: str,
        *,
        passed: bool,
        evidence_ref: str,
        reasons: tuple[str, ...] = (),
    ) -> SkillCandidate:
        return self._transition(
            candidate_id,
            allowed={FoundryState.DISCOVERED, FoundryState.QUARANTINED},
            target=FoundryState.SCANNED,
            evidence_ref=evidence_ref,
            passed=passed,
            reasons=reasons,
            score_delta=0.20,
        )

    def record_sandbox_test(
        self,
        candidate_id: str,
        *,
        passed: bool,
        evidence_ref: str,
        reasons: tuple[str, ...] = (),
    ) -> SkillCandidate:
        return self._transition(
            candidate_id,
            allowed={FoundryState.SCANNED},
            target=FoundryState.SANDBOX_TESTED,
            evidence_ref=evidence_ref,
            passed=passed,
            reasons=reasons,
            score_delta=0.15,
        )

    def record_benchmark(
        self,
        candidate_id: str,
        *,
        passed: bool,
        evidence_ref: str,
        reasons: tuple[str, ...] = (),
    ) -> SkillCandidate:
        return self._transition(
            candidate_id,
            allowed={FoundryState.SANDBOX_TESTED},
            target=FoundryState.BENCHMARKED,
            evidence_ref=evidence_ref,
            passed=passed,
            reasons=reasons,
            score_delta=0.10,
        )

    def record_compatibility(
        self,
        candidate_id: str,
        *,
        passed: bool,
        evidence_ref: str,
        reasons: tuple[str, ...] = (),
    ) -> SkillCandidate:
        candidate = self._transition(
            candidate_id,
            allowed={FoundryState.BENCHMARKED},
            target=FoundryState.COMPATIBLE,
            evidence_ref=evidence_ref,
            passed=passed,
            reasons=reasons,
            score_delta=0.10,
        )
        if candidate.state is FoundryState.COMPATIBLE:
            self.ledger.append(
                "skill_foundry_assessed",
                {
                    "candidate_id": candidate_id,
                    "state": FoundryState.AWAITING_APPROVAL.value,
                    "evidence_ref": evidence_ref,
                    "passed": True,
                    "trust_score": candidate.trust_score,
                    "reasons": [],
                },
            )
        return self._state()[candidate_id]

    def approve(
        self, candidate_id: str, *, approved_by: str, evidence_ref: str
    ) -> SkillCandidate:
        candidate = self._state().get(candidate_id)
        if candidate is None:
            raise KeyError(candidate_id)
        if candidate.state is not FoundryState.AWAITING_APPROVAL:
            raise RuntimeError("candidate is not awaiting approval")
        if approved_by.strip().lower() != "human_governor":
            raise PermissionError("skill promotion requires human_governor approval")
        self.ledger.append(
            "skill_foundry_assessed",
            {
                "candidate_id": candidate_id,
                "state": FoundryState.REGISTERABLE.value,
                "evidence_ref": evidence_ref.strip(),
                "passed": True,
                "trust_score": candidate.trust_score,
                "reasons": [],
                "activation_allowed": False,
                "registration_requires_explicit_action": True,
            },
        )
        return self._state()[candidate_id]
