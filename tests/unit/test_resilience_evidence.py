import json
from datetime import UTC, datetime

from creator_app.core.resilience_evidence import HashLinkedEvidenceStore


def test_evidence_chain_is_hash_linked_and_verifiable(tmp_path) -> None:
    store = HashLinkedEvidenceStore(tmp_path / "evidence.jsonl")
    now = datetime(2026, 8, 21, 10, tzinfo=UTC)

    first = store.append(
        event_type="test.started",
        subject="subject:1",
        payload_digest=store.payload_digest({"step": 1}),
        created_at=now,
    )
    second = store.append(
        event_type="test.completed",
        subject="subject:1",
        payload_digest=store.payload_digest({"step": 2}),
        created_at=now,
    )

    assert first.previous_hash == store.GENESIS_HASH
    assert second.previous_hash == first.record_hash
    assert store.verify_chain() is True


def test_evidence_chain_detects_tampering(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    store = HashLinkedEvidenceStore(path)
    now = datetime(2026, 8, 21, 10, tzinfo=UTC)
    store.append(
        event_type="test.completed",
        subject="subject:1",
        payload_digest=store.payload_digest({"result": "pass"}),
        created_at=now,
    )

    record = json.loads(path.read_text(encoding="utf-8"))
    record["subject"] = "subject:tampered"
    path.write_text(json.dumps(record) + "\n", encoding="utf-8")

    assert store.verify_chain() is False


def test_evidence_store_persists_digest_not_raw_payload(tmp_path) -> None:
    path = tmp_path / "evidence.jsonl"
    store = HashLinkedEvidenceStore(path)
    payload = {"credential": "raw-secret-value"}
    store.append(
        event_type="security.test",
        subject="subject:1",
        payload_digest=store.payload_digest(payload),
        created_at=datetime(2026, 8, 21, 10, tzinfo=UTC),
    )

    persisted = path.read_text(encoding="utf-8")
    assert "raw-secret-value" not in persisted
