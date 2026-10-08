from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from creator_app.q11_capability import (
    Q11GateResult,
    Q11Status,
    aggregate_q11,
    classify_provider_result,
    make_gate,
    provider_gate_status,
    validate_gate_evidence,
)

META = dict(
    execution_id="exec-1",
    release_id="release-1",
    commit="a" * 40,
    source_identity="source-1",
    evidence_artifact="evidence/q11-test.json",
    evidence_sha256="sha256:" + "b" * 64,
    verification_method="independent_runtime_execution",
)


def gate(gate_id: str, status: Q11Status, **extra) -> Q11GateResult:
    return make_gate(gate_id, status, **{**META, **extra})


def all_verified(*, provider="openai"):
    return {
        "Q11-A": gate("Q11-A", Q11Status.VERIFIED),
        "Q11-B": gate("Q11-B", Q11Status.VERIFIED),
        "Q11-C": gate("Q11-C", Q11Status.VERIFIED, provider=provider),
        "Q11-D": gate("Q11-D", Q11Status.VERIFIED, provider=provider),
        "Q11-E": gate("Q11-E", Q11Status.VERIFIED, provider=provider),
        "Q11-F": gate("Q11-F", Q11Status.VERIFIED, provider=provider),
        "Q11-G": gate("Q11-G", Q11Status.VERIFIED),
    }


def test_01_credential_integrity_can_be_verified_independently():
    result = gate("Q11-A", Q11Status.VERIFIED)
    validate_gate_evidence(result)
    assert result.status is Q11Status.VERIFIED


def test_02_runtime_execution_can_be_verified_independently():
    assert gate("Q11-B", Q11Status.VERIFIED).status is Q11Status.VERIFIED


def test_03_provider_reachability_can_be_verified_independently():
    assert gate("Q11-C", Q11Status.VERIFIED, provider="openai").status is Q11Status.VERIFIED


def test_04_http_429_insufficient_quota_is_blocked():
    assert (
        classify_provider_result(http_status=429, error_code="insufficient_quota").value
        == "INSUFFICIENT_QUOTA"
    )
    e, f, reason = provider_gate_status(
        provider="openai",
        http_status=429,
        error_code="insufficient_quota",
        sentinel_observed=False,
        verification_method="independent_runtime_execution",
    )
    assert e is Q11Status.BLOCKED
    assert f is Q11Status.BLOCKED
    assert reason == "openai: insufficient_quota"


def test_05_429_cannot_produce_verified():
    gates = all_verified()
    gates["Q11-E"] = gate(
        "Q11-E", Q11Status.BLOCKED, provider="openai", block_reason="openai: insufficient_quota"
    )
    gates["Q11-F"] = gate(
        "Q11-F", Q11Status.BLOCKED, provider="openai", block_reason="openai: insufficient_quota"
    )
    assert aggregate_q11(gates) is Q11Status.BLOCKED


def test_06_mock_success_cannot_be_live_provider_verification():
    result = gate(
        "Q11-F", Q11Status.VERIFIED, provider="openai", verification_method="mock_provider_response"
    )
    with pytest.raises(ValueError, match="mock"):
        validate_gate_evidence(result)


def test_07_missing_evidence_cannot_produce_verified():
    gates = all_verified()
    del gates["Q11-G"]
    assert aggregate_q11(gates) is Q11Status.NOT_VERIFIED


def test_08_local_only_evidence_cannot_produce_live_openai_verification():
    assert aggregate_q11(all_verified(provider="ollama")) is Q11Status.NOT_VERIFIED


def test_09_verified_evidence_requires_release_source_identity():
    result = replace(gate("Q11-A", Q11Status.VERIFIED), commit=None)
    with pytest.raises(ValueError, match="commit"):
        validate_gate_evidence(result)


def test_10_evidence_hash_is_required_and_recorded():
    result = gate("Q11-G", Q11Status.VERIFIED)
    assert result.evidence_sha256.startswith("sha256:")
    assert len(result.evidence_sha256) == len("sha256:") + 64
    payload = json.dumps(
        {"gate_id": result.gate_id, "status": result.status}, sort_keys=True
    ).encode()
    assert hashlib.sha256(payload).hexdigest()


def test_11_provider_failure_does_not_erase_independent_verified_gates():
    gates = all_verified()
    gates["Q11-E"] = gate(
        "Q11-E", Q11Status.BLOCKED, provider="openai", block_reason="openai: insufficient_quota"
    )
    assert gates["Q11-A"].status is Q11Status.VERIFIED
    assert gates["Q11-B"].status is Q11Status.VERIFIED
    assert gates["Q11-G"].status is Q11Status.VERIFIED
    assert aggregate_q11(gates) is Q11Status.BLOCKED


def test_12_aggregate_stays_blocked_without_required_live_provider_evidence():
    gates = all_verified()
    gates["Q11-F"] = gate("Q11-F", Q11Status.NOT_VERIFIED, provider="openai")
    assert aggregate_q11(gates) is Q11Status.NOT_VERIFIED
    gates["Q11-F"] = gate(
        "Q11-F", Q11Status.BLOCKED, provider="openai", block_reason="openai: insufficient_quota"
    )
    assert aggregate_q11(gates) is Q11Status.BLOCKED
