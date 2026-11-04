from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_proposal(
    claim: dict[str, Any],
    summary: dict[str, Any],
    *,
    evidence_path: str,
    evidence_sha256: str,
    output_digest: str,
    captured_at: str,
) -> dict[str, Any]:
    if claim.get("state") != "TARGET":
        raise ValueError("only TARGET claims can use the benchmark transition proposer")
    if summary.get("schema") != "ck-nexus.termux-benchmark.v2":
        raise ValueError("unsupported benchmark summary schema")
    if summary.get("claim_id") != claim.get("claim_id"):
        raise ValueError("benchmark claim_id does not match registry claim")
    if summary.get("claim_status") != "MEASURED_NOT_VERIFIED":
        raise ValueError("benchmark summary must remain MEASURED_NOT_VERIFIED")

    subject = claim.get("subject")
    if not isinstance(subject, dict):
        raise ValueError("claim subject is missing")
    subject_commit = summary.get("subject_commit")
    if subject_commit != subject.get("commit"):
        raise ValueError("benchmark subject commit does not match claim subject commit")

    runs = summary.get("rounds")
    if not isinstance(runs, int) or runs < 3:
        raise ValueError("benchmark must contain at least 3 measured rounds")

    method = summary.get("measurement_method")
    if not isinstance(method, str) or not method.strip():
        raise ValueError("benchmark measurement_method is required")
    limitations = summary.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        raise ValueError("benchmark limitations are required")
    if any(not isinstance(item, str) or not item.strip() for item in limitations):
        raise ValueError("benchmark limitations must be non-empty strings")

    device = summary.get("device")
    if not isinstance(device, dict):
        raise ValueError("benchmark device metadata is required")
    mem_total_kib = device.get("mem_total_kib")
    if not isinstance(mem_total_kib, int) or mem_total_kib <= 0:
        raise ValueError("device.mem_total_kib must be a positive integer")

    layers = summary.get("layers_completed")
    if not isinstance(layers, list) or not layers:
        raise ValueError("benchmark layers_completed is required")

    benchmark = claim.get("benchmark")
    if not isinstance(benchmark, dict):
        raise ValueError("claim benchmark contract is missing")

    return {
        "schema": "ck-nexus.claim-transition-proposal.v1",
        "claim_id": claim["claim_id"],
        "from_state": "TARGET",
        "to_state": "MEASURED_NOT_VERIFIED",
        "subject_commit": subject_commit,
        "created_at": captured_at,
        "automatic_promotion_allowed": False,
        "verifier_required_for_verified": True,
        "benchmark": {
            "protocol_ref": benchmark.get("protocol_ref"),
            "harness_commit": subject_commit,
            "layers_completed": layers,
            "runs": runs,
            "aggregation": "median",
            "measurement_method": method,
            "measurement_limitations": " ".join(limitations),
            "device": device,
            "memory": summary.get("memory"),
            "latency_ms": summary.get("latency_ms"),
        },
        "evidence": {
            "evidence_path": evidence_path,
            "evidence_sha256": evidence_sha256,
            "exit_code": 0,
            "output_digest": output_digest,
            "timestamp": captured_at,
        },
        "proposed_history_entry": {
            "from_state": "TARGET",
            "to_state": "MEASURED_NOT_VERIFIED",
            "at": captured_at,
            "reason": (
                "Physical-device benchmark evidence was captured; independent "
                "verification is still required."
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    claim = _load(args.claim)
    summary = _load(args.summary)
    proposal = build_proposal(
        claim,
        summary,
        evidence_path=args.evidence_path,
        evidence_sha256=_sha256(args.summary),
        output_digest=_sha256(args.manifest),
        captured_at=datetime.now(UTC).isoformat(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "claim_id": proposal["claim_id"],
                "proposal": str(args.output),
                "to_state": proposal["to_state"],
                "automatic_promotion_allowed": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
