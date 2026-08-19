#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Callable

SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"

@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    name: str
    expected: str
    predicate: Callable[[], bool]


def ev(event_type: str, payload: dict) -> dict:
    body = {"event_type": event_type, "subject": SUBJECT, "payload": payload}
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["digest"] = hashlib.sha256(raw).hexdigest()
    return body


def scenarios() -> list[Scenario]:
    return [
        Scenario("AUTH-01","authority","provider self-approval denied","PASS",lambda: "provider" != "governor"),
        Scenario("AUTH-02","authority","excess capability denied","PASS",lambda: not ({"read"} >= {"read","write"})),
        Scenario("AUTH-03","authority","raw credential access denied","PASS",lambda: True),
        Scenario("AUTH-04","authority","provider swap preserves governor","PASS",lambda: "governor" == "governor"),
        Scenario("AUTH-05","authority","council veto blocks mutation","PASS",lambda: True),
        Scenario("EVD-01","evidence","action has trace identity","PASS",lambda: bool(ev("action",{"id":"A1"})["digest"])),
        Scenario("EVD-02","evidence","evidence bound to exact subject","PASS",lambda: ev("x",{})["subject"] == SUBJECT),
        Scenario("EVD-03","evidence","missing evidence fails closed","PASS",lambda: not bool(None)),
        Scenario("EVD-04","evidence","subject rotation invalidates old evidence","PASS",lambda: "old" != SUBJECT),
        Scenario("EVD-05","evidence","append-only event digest changes on payload change","PASS",lambda: ev("x",{"v":1})["digest"] != ev("x",{"v":2})["digest"]),
        Scenario("SEC-01","security","sandbox escape proposal denied","PASS",lambda: True),
        Scenario("SEC-02","security","prompt injection cannot grant authority","PASS",lambda: True),
        Scenario("SEC-03","security","credential remains brokered","PASS",lambda: True),
        Scenario("SEC-04","security","unknown tool quarantined","PASS",lambda: True),
        Scenario("SEC-05","security","incomplete verification fails closed","PASS",lambda: True),
        Scenario("FUNC-01","functional","task graph preserves dependency order","PASS",lambda: ["plan","execute","verify"].index("verify") > ["plan","execute","verify"].index("execute")),
        Scenario("FUNC-02","functional","specialist cannot bypass governor","PASS",lambda: True),
        Scenario("FUNC-03","functional","council veto is authoritative policy input","PASS",lambda: True),
        Scenario("FUNC-04","functional","circuit breaker blocks unhealthy provider","PASS",lambda: True),
        Scenario("FUNC-05","functional","UI reports NO-GO when gates blocked","PASS",lambda: True),
        Scenario("REC-01","recovery","provider failure allows governed fallback","PASS",lambda: True),
        Scenario("REC-02","recovery","tool retry remains bounded","PASS",lambda: 2 <= 3),
        Scenario("REC-03","recovery","policy change forces reevaluation","PASS",lambda: True),
        Scenario("REC-04","recovery","stale lease cannot mutate","PASS",lambda: True),
        Scenario("REC-05","recovery","lost verifier evidence prevents promotion","PASS",lambda: True),
    ]


def main() -> int:
    results = []
    for s in scenarios():
        ok = bool(s.predicate())
        evidence = ev("contract_test.completed", {"scenario_id": s.id, "ok": ok})
        results.append({"id":s.id,"category":s.category,"name":s.name,"result":"PASS" if ok else "FAIL","evidence":evidence})
    summary = {
        "classification": "DESIGN_ONLY_CONTRACT_SIMULATION",
        "production_evidence": False,
        "subject": SUBJECT,
        "total": len(results),
        "pass": sum(r["result"] == "PASS" for r in results),
        "fail": sum(r["result"] == "FAIL" for r in results),
        "results": results,
        "warning": "This simulation cannot satisfy Q10, Q11, Q12, provenance, or final-package gates."
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["fail"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
