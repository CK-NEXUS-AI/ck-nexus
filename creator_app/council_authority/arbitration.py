from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Proposal:
    agent_id: str
    option: str
    evidence_refs: list[str] = field(default_factory=list)
    verifier_score: float = 0.0
    risk: str = "low"
    reason: str = ""
    is_safety_veto: bool = False


class ArbitrationEngine:
    def __init__(self, contract: dict, store, *, evidence_threshold: float = 0.34):
        self.contract = contract
        self.store = store
        self.threshold = evidence_threshold

    def _authorized_veto(self, p: Proposal, domain: str, task_id: str) -> bool:
        a = self.contract.get("agents", {}).get(p.agent_id, {})
        scopes = a.get("canVeto", [])
        return (
            p.is_safety_veto
            and (domain in scopes or "*" in scopes)
            and self.store.evidence_quality(p.evidence_refs, task_id=task_id) > 0
        )

    def _score(self, p: Proposal, domain: str, task_id: str) -> float:
        evidence = self.store.evidence_quality(p.evidence_refs, task_id=task_id)
        owner = (
            1.0
            if self.contract.get("agents", {}).get(p.agent_id, {}).get("domain") == domain
            else 0.0
        )
        verifier = max(0, min(float(p.verifier_score), 1))
        risk = {"low": 0, "medium": 0.15, "high": 0.35}.get(p.risk, 0.35)
        return 0.45 * evidence + 0.25 * owner + 0.30 * verifier - risk

    def resolve(
        self, decision_id: str, domain: str, proposals: list[Proposal], *, high_risk: bool = False
    ) -> dict:
        veto = next((p for p in proposals if self._authorized_veto(p, domain, decision_id)), None)
        if veto and (high_risk or veto.risk == "high"):
            out = {
                "decisionId": decision_id,
                "status": "BLOCKED_SAFETY_VETO",
                "vetoBy": veto.agent_id,
                "reason": veto.reason or "verified safety veto",
            }
            self.store.append_audit({"type": "decision", "domain": domain, **out})
            return out
        scored = sorted(
            ((p, self._score(p, domain, decision_id)) for p in proposals), key=lambda x: x[1], reverse=True
        )
        if not scored:
            return {
                "decisionId": decision_id,
                "status": "BLOCKED_HUMAN_REVIEW",
                "reason": "no proposals",
            }
        top, score = scored[0]
        runner = scored[1][1] if len(scored) > 1 else -99
        if score - runner < self.threshold:
            out = {
                "decisionId": decision_id,
                "status": "BLOCKED_HUMAN_REVIEW",
                "scores": {p.agent_id: round(s, 3) for p, s in scored},
                "reason": "insufficient verified evidence margin",
            }
            self.store.append_audit({"type": "decision", "domain": domain, **out})
            return out
        out = {
            "decisionId": decision_id,
            "status": "RESOLVED",
            "selectedOption": top.option,
            "approver": top.agent_id,
            "scores": {p.agent_id: round(s, 3) for p, s in scored},
        }
        self.store.append_audit({"type": "decision", "domain": domain, **out})
        return out
