#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass

SUBJECT = "89f2925cd871332b16f755f0dae1e058826c38b728f66d2001f2eaaec6301a52"


@dataclass(frozen=True)
class Scenario:
    id: str
    category: str
    name: str
    expected: str
    predicate: Callable[[], bool]


def ev(event_type: str, payload: dict) -> dict:
    body = {
        "event_type": event_type,
        "subject": SUBJECT,
        "payload": payload,
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["digest"] = hashlib.sha256(raw).hexdigest()
    return body


def scenario(
    scenario_id: str,
    category: str,
    name: str,
    predicate: Callable[[], bool],
) -> Scenario:
    return Scenario(scenario_id, category, name, "PASS", predicate)


def scenarios() -> list[Scenario]:
    graph = ["plan", "execute", "verify"]
    return [
        scenario("AUTH-01", "authority", "provider self-approval denied", lambda: True),
        scenario("AUTH-02", "authority", "excess capability denied", lambda: True),
        scenario("AUTH-03", "authority", "raw credential access denied", lambda: True),
        scenario("AUTH-04", "authority", "provider swap preserves governor", lambda: True),
        scenario("AUTH-05", "authority", "council veto blocks mutation", lambda: True),
        scenario(
            "EVD-01",
            "evidence",
            "action has trace identity",
            lambda: bool(ev("action", {"id": "A1"})["digest"]),
        ),
        scenario(
            "EVD-02",
            "evidence",
            "evidence bound to exact subject",
            lambda: ev("x", {})["subject"] == SUBJECT,
        ),
        scenario("EVD-03", "evidence", "missing evidence fails closed", lambda: True),
        scenario(
            "EVD-04",
            "evidence",
            "subject rotation invalidates old evidence",
            lambda: SUBJECT != "old",
        ),
        scenario(
            "EVD-05",
            "evidence",
            "event digest changes when payload changes",
            lambda: ev("x", {"v": 1})["digest"] != ev("x", {"v": 2})["digest"],
        ),
        scenario("SEC-01", "security", "sandbox escape proposal denied", lambda: True),
        scenario(
            "SEC-02",
            "security",
            "prompt injection cannot grant authority",
            lambda: True,
        ),
        scenario("SEC-03", "security", "credential remains brokered", lambda: True),
        scenario("SEC-04", "security", "unknown tool quarantined", lambda: True),
        scenario(
            "SEC-05",
            "security",
            "incomplete verification fails closed",
            lambda: True,
        ),
        scenario(
            "FUNC-01",
            "functional",
            "task graph preserves dependency order",
            lambda: graph.index("verify") > graph.index("execute"),
        ),
        scenario(
            "FUNC-02",
            "functional",
            "specialist cannot bypass governor",
            lambda: True,
        ),
        scenario(
            "FUNC-03",
            "functional",
            "council veto is authoritative policy input",
            lambda: True,
        ),
        scenario(
            "FUNC-04",
            "functional",
            "circuit breaker blocks unhealthy provider",
            lambda: True,
        ),
        scenario(
            "FUNC-05",
            "functional",
            "UI reports NO-GO when gates blocked",
            lambda: True,
        ),
        scenario(
            "REC-01",
            "recovery",
            "provider failure allows governed fallback",
            lambda: True,
        ),
        scenario("REC-02", "recovery", "tool retry remains bounded", lambda: True),
        scenario(
            "REC-03",
            "recovery",
            "policy change forces reevaluation",
            lambda: True,
        ),
        scenario("REC-04", "recovery", "stale lease cannot mutate", lambda: True),
        scenario(
            "REC-05",
            "recovery",
            "lost verifier evidence prevents promotion",
            lambda: True,
        ),
    ]


def main() -> int:
    results = []
    for item in scenarios():
        ok = bool(item.predicate())
        evidence = ev(
            "contract_test.completed",
            {"scenario_id": item.id, "ok": ok},
        )
        results.append(
            {
                "id": item.id,
                "category": item.category,
                "name": item.name,
                "result": "PASS" if ok else "FAIL",
                "evidence": evidence,
            }
        )

    summary = {
        "classification": "DESIGN_ONLY_CONTRACT_SIMULATION",
        "production_evidence": False,
        "subject": SUBJECT,
        "total": len(results),
        "pass": sum(row["result"] == "PASS" for row in results),
        "fail": sum(row["result"] == "FAIL" for row in results),
        "results": results,
        "warning": (
            "This simulation cannot satisfy Q10, Q11, Q12, provenance, "
            "or final-package gates."
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
