from __future__ import annotations

import concurrent.futures
from datetime import UTC, datetime, timedelta
from pathlib import Path

from services.email_gateway.repository import EmailGatewayRepository


def repo(tmp_path: Path) -> EmailGatewayRepository:
    store = EmailGatewayRepository(tmp_path / "email.db")
    store.initialize()
    return store


def test_atomic_provider_identity_deduplicates_100_concurrent_claims(tmp_path: Path):
    store = repo(tmp_path)

    def claim(index: int) -> bool:
        return store.claim_message(
            mailbox="admin@ck-nexus.test",
            provider="gmail",
            provider_message_id="gmail-provider-id-001",
            internet_message_id="<spoofable-header@example.test>",
            claimed_by=f"worker-{index}",
        ).claimed

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        results = list(pool.map(claim, range(100)))

    assert sum(results) == 1
    assert store.count_journal() == 1


def test_same_internet_message_id_does_not_collapse_distinct_provider_ids(tmp_path: Path):
    store = repo(tmp_path)
    for provider_id in ("gmail-1", "gmail-2"):
        result = store.claim_message(
            mailbox="admin@ck-nexus.test",
            provider="gmail",
            provider_message_id=provider_id,
            internet_message_id="<same-header@example.test>",
            claimed_by="worker",
        )
        assert result.claimed is True
    assert store.count_journal() == 2


def test_outbox_dedup_and_retry_preserves_side_effect_intent(tmp_path: Path):
    store = repo(tmp_path)
    journal = store.claim_message(
        mailbox="admin@ck-nexus.test",
        provider="gmail",
        provider_message_id="gmail-2",
        claimed_by="worker",
    )
    assert journal.journal_id
    created, outbox_id = store.enqueue_outbox(
        email_journal_id=journal.journal_id,
        action_type="email.reply",
        destination="user@example.test",
        payload={"subject": "hello", "text": "world"},
        deduplication_key=f"reply:{journal.journal_id}:v1",
    )
    assert created is True
    duplicate_created, duplicate_id = store.enqueue_outbox(
        email_journal_id=journal.journal_id,
        action_type="email.reply",
        destination="user@example.test",
        payload={"subject": "hello", "text": "world"},
        deduplication_key=f"reply:{journal.journal_id}:v1",
    )
    assert duplicate_created is False
    assert duplicate_id == outbox_id
    assert store.count_outbox() == 1

    def failing_sender(_):
        raise TimeoutError("provider accepted state is uncertain")

    outcome = store.run_outbox_once(worker_id="sender-1", sender=failing_sender)
    assert outcome == {"claimed": 1, "sent": 0, "retry": 1}
    row = store.get_outbox(outbox_id)
    assert row is not None
    assert row["status"] == "FAILED_RETRYABLE"
    assert row["sent_at"] is None
    assert row["attempt_count"] == 1


def test_expired_processing_and_outbox_leases_are_recovered(tmp_path: Path):
    store = repo(tmp_path)
    t0 = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
    journal = store.claim_message(
        mailbox="admin@ck-nexus.test",
        provider="gmail",
        provider_message_id="gmail-expired",
        claimed_by="dead-worker",
        lease_seconds=1,
        now=t0,
    )
    assert journal.journal_id
    created, outbox_id = store.enqueue_outbox(
        email_journal_id=journal.journal_id,
        action_type="email.reply",
        destination="user@example.test",
        payload={"text": "reply"},
        deduplication_key=f"reply:{journal.journal_id}:v1",
        now=t0,
    )
    assert created
    claimed = store.claim_outbox_batch(
        worker_id="dead-sender",
        lease_seconds=1,
        now=t0,
    )
    assert [item.id for item in claimed] == [outbox_id]

    recovered = store.recover_expired_leases(now=t0 + timedelta(seconds=2))
    assert recovered == {"journal": 1, "outbox": 1}
    assert store.get_journal(journal.journal_id)["status"] == "FAILED_RETRYABLE"
    assert store.get_outbox(outbox_id)["status"] == "FAILED_RETRYABLE"


def test_email_gateway_api_requires_token_and_deduplicates(tmp_path: Path):
    from fastapi.testclient import TestClient

    from creator_app.api import create_app
    from creator_app.config import Settings

    settings = Settings(
        database_path=tmp_path / "creator.db",
        mock_ai=True,
        email_gateway_enabled=True,
        email_database_path=tmp_path / "email.db",
        email_webhook_token="webhook-test-secret",
        email_lease_seconds=300,
    )
    payload = {
        "mailbox": "admin@ck-nexus.test",
        "provider": "gmail",
        "provider_message_id": "gmail-api-1",
        "internet_message_id": "<header@example.test>",
        "execution_id": "ck-worker-execution-1",
    }
    with TestClient(create_app(settings)) as client:
        assert client.post("/api/email/ingest", json=payload).status_code == 401
        headers = {"X-CK-NEXUS-Webhook-Token": "webhook-test-secret"}
        first = client.post("/api/email/ingest", json=payload, headers=headers)
        second = client.post("/api/email/ingest", json=payload, headers=headers)
        assert first.status_code == 200
        assert first.json()["status"] == "accepted"
        assert second.status_code == 200
        assert second.json()["status"] == "duplicate"
        assert first.json()["journal_id"] == second.json()["journal_id"]

        outbox_payload = {
            "journal_id": first.json()["journal_id"],
            "action_type": "email.reply",
            "destination": "user@example.test",
            "payload": {"text": "reply"},
            "deduplication_key": f"reply:{first.json()['journal_id']}:v1",
        }
        queued = client.post("/api/email/outbox", json=outbox_payload, headers=headers)
        duplicate = client.post("/api/email/outbox", json=outbox_payload, headers=headers)
        assert queued.status_code == 200
        assert queued.json()["created"] is True
        assert duplicate.status_code == 200
        assert duplicate.json()["created"] is False
        assert queued.json()["outbox_id"] == duplicate.json()["outbox_id"]


def test_deterministic_routing_prioritizes_security_and_aliases():
    from services.email_gateway.routing import route_email

    cases = [
        ({"matched_alias": "security@ck-nexus.test", "subject": "newsletter"}, "SECURITY"),
        ({"matched_alias": "billing@ck-nexus.test", "subject": "hello"}, "BILLING"),
        ({"matched_alias": "github@ck-nexus.test", "subject": "hello"}, "DEVOPS"),
        ({"matched_alias": "alerts@ck-nexus.test", "subject": "hello"}, "SYSTEM_ALERT"),
        ({"matched_alias": "support@ck-nexus.test", "subject": "hello"}, "SUPPORT"),
        ({"matched_alias": "ai@ck-nexus.test", "subject": "hello"}, "AI_REQUEST"),
        ({"matched_alias": None, "subject": "Payment failed for production"}, "BILLING"),
        ({"matched_alias": None, "subject": "CI build failed"}, "DEVOPS"),
        ({"matched_alias": None, "subject": "Possible credential breach"}, "SECURITY"),
        ({"matched_alias": None, "subject": "general greeting"}, "UNKNOWN"),
    ]
    for payload, expected in cases:
        assert route_email(**payload).category == expected


def test_loop_prevention_blocks_automation_and_system_mail():
    from services.email_gateway.loop_prevention import evaluate_loop_headers

    assert evaluate_loop_headers({"X-CK-NEXUS-Loop": "evt-1"}).allow_automatic_reply is False
    assert evaluate_loop_headers({"Auto-Submitted": "auto-replied"}).allow_automatic_reply is False
    assert evaluate_loop_headers({"Precedence": "bulk"}).allow_automatic_reply is False
    assert (
        evaluate_loop_headers({"From": "MAILER-DAEMON@example.test"}).allow_automatic_reply is False
    )
    assert evaluate_loop_headers({"From": "person@example.test"}).allow_automatic_reply is True


def test_attachment_quarantine_blocks_executable_and_suspicious_zip(tmp_path: Path):
    import zipfile

    from services.email_gateway.attachments import scan_attachment

    executable = tmp_path / "payload.exe"
    executable.write_bytes(b"MZ" + b"x" * 32)
    result = scan_attachment(executable)
    assert result.safe is False
    assert result.status == "QUARANTINE"

    archive = tmp_path / "bomb.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        handle.writestr("huge.txt", "A" * 2_000_000)
    result = scan_attachment(archive, max_zip_ratio=10.0)
    assert result.safe is False
    assert result.reason == "zip_compression_ratio"


def test_audit_trace_is_complete_and_queryable(tmp_path: Path):
    store = repo(tmp_path)
    claim = store.claim_message(
        mailbox="admin@ck-nexus.test",
        provider="gmail",
        provider_message_id="trace-1",
        claimed_by="ck-worker-1",
    )
    assert claim.journal_id
    store.audit(
        email_journal_id=claim.journal_id,
        event_type="INGRESS_ACCEPTED",
        actor_type="cknexus-email-worker",
        actor_id="ck-worker-1",
        action="claim",
        result="PASS",
    )
    store.audit(
        email_journal_id=claim.journal_id,
        event_type="ROUTED",
        routing_category="SUPPORT",
        action="dispatch",
        result="PASS",
        details={"rule": "R-ALIAS-SUPPORT"},
    )
    trace = store.trace_audit(claim.journal_id)
    assert [row["event_type"] for row in trace] == ["INGRESS_ACCEPTED", "ROUTED"]
    assert trace[1]["details"]["rule"] == "R-ALIAS-SUPPORT"


def test_metrics_and_api_audit_trace(tmp_path: Path):
    from fastapi.testclient import TestClient

    from creator_app.api import create_app
    from creator_app.config import Settings

    settings = Settings(
        database_path=tmp_path / "creator.db",
        mock_ai=True,
        email_gateway_enabled=True,
        email_database_path=tmp_path / "email.db",
        email_webhook_token="webhook-test-secret",
    )
    headers = {"X-CK-NEXUS-Webhook-Token": "webhook-test-secret"}
    with TestClient(create_app(settings)) as client:
        payload = {
            "mailbox": "admin@ck-nexus.test",
            "provider": "gmail",
            "provider_message_id": "metrics-1",
            "execution_id": "ck-worker-metrics",
        }
        response = client.post("/api/email/ingest", json=payload, headers=headers)
        journal_id = response.json()["journal_id"]
        client.post("/api/email/ingest", json=payload, headers=headers).raise_for_status()

        trace = client.get(f"/api/email/audit/{journal_id}", headers=headers)
        assert trace.status_code == 200
        assert [event["event_type"] for event in trace.json()["events"]] == [
            "INGRESS_ACCEPTED",
            "INGRESS_DUPLICATE",
        ]

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "ckn_email_journal_total 1" in metrics.text
        assert "ckn_email_duplicate_total 1" in metrics.text


def test_internal_email_worker_endpoints_route_loop_scan_and_outbox(tmp_path: Path):
    from fastapi.testclient import TestClient

    from creator_app.api import create_app
    from creator_app.config import Settings

    settings = Settings(
        database_path=tmp_path / "creator.db",
        mock_ai=True,
        email_gateway_enabled=True,
        email_database_path=tmp_path / "email.db",
        email_webhook_token="gateway-token",
    )
    headers = {"X-CK-NEXUS-Webhook-Token": "gateway-token"}
    with TestClient(create_app(settings)) as client:
        route = client.post(
            "/api/email/route",
            headers=headers,
            json={"matched_alias": "billing@ck-nexus.test", "subject": "invoice"},
        )
        assert route.status_code == 200
        assert route.json()["category"] == "BILLING"

        loop = client.post(
            "/api/email/loop-check",
            headers=headers,
            json={"headers": {"Auto-Submitted": "auto-replied"}},
        )
        assert loop.status_code == 200
        assert loop.json()["allow_automatic_reply"] is False

        scan = client.post(
            "/api/email/scan-attachment",
            headers=headers,
            files={"file": ("payload.exe", b"MZ1234", "application/octet-stream")},
        )
        assert scan.status_code == 200
        assert scan.json()["status"] == "QUARANTINE"

        ingress = client.post(
            "/api/email/ingest",
            headers=headers,
            json={
                "mailbox": "admin@ck-nexus.test",
                "provider": "gmail",
                "provider_message_id": "worker-api-1",
                "execution_id": "ck-worker-ingress",
            },
        ).json()
        enqueue = client.post(
            "/api/email/outbox",
            headers=headers,
            json={
                "journal_id": ingress["journal_id"],
                "action_type": "email.reply",
                "destination": "user@example.test",
                "payload": {"text": "hello"},
                "deduplication_key": "worker-api-1:reply:v1",
            },
        ).json()
        claimed = client.post(
            "/api/email/outbox/claim",
            headers=headers,
            json={"worker_id": "ck-outbox-1", "limit": 10, "lease_seconds": 120},
        )
        assert claimed.status_code == 200
        assert [item["id"] for item in claimed.json()["items"]] == [enqueue["outbox_id"]]
        sent = client.post(
            f"/api/email/outbox/{enqueue['outbox_id']}/sent",
            headers=headers,
            json={"provider_message_id": "gmail-sent-1"},
        )
        assert sent.status_code == 200
        assert sent.json()["status"] == "sent"

        recovered = client.post("/api/email/recover", headers=headers)
        assert recovered.status_code == 200
        assert recovered.json() == {"journal": 0, "outbox": 0}
