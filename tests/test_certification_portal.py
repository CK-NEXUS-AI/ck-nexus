"""Regression tests for the read-only certification assessment prototype."""

import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient

from certification_portal import app as portal_app
from certification_portal.app import app

client = TestClient(app)


def test_health_disables_certificate_issuance() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "mode": "ASSESSMENT_DEMO",
        "certificate_issuance": "disabled",
    }


def test_portal_homepage_is_served() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "CK-NEXUS" in response.text


def test_local_assessment_fails_closed_while_policy_is_draft() -> None:
    response = client.post("/api/assess/local")

    assert response.status_code == 200
    result = response.json()
    assert result["result"] == "NOT_CERTIFIED"
    assert any(
        check["control"] == "CKN-GOV-001_POLICY_ADOPTION" and check["result"] == "FAIL"
        for check in result["checks"]
    )
    assert "No certificate is issued by this prototype." in result["limitations"]


def test_owner_signoff_preview_rejects_missing_consent() -> None:
    response = client.post(
        "/api/owner-signoff-preview",
        json={
            "full_name": "Test Owner",
            "role": "System Owner",
            "consent": False,
            "subject_digest": "0" * 64,
            "profile_id": "test-profile",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Owner consent is required"


def test_owner_signoff_preview_is_cryptographically_verifiable_but_demo_only() -> None:
    response = client.post(
        "/api/owner-signoff-preview",
        json={
            "full_name": "Test Owner",
            "role": "System Owner",
            "consent": True,
            "subject_digest": "0" * 64,
            "profile_id": "test-profile",
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "OWNER_SIGNOFF_PREVIEW_ONLY"
    assert "identity authentication" in result["notice"]

    key_response = client.get("/api/demo-key")
    assert key_response.status_code == 200
    key = key_response.json()
    assert key["trust"] == "NON_PRODUCTION_EPHEMERAL"
    assert key["algorithm"] == "Ed25519"

    signed_body = {
        name: value
        for name, value in result.items()
        if name not in {"digest", "demo_signature", "key_id"}
    }
    canonical = json.dumps(signed_body, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == result["digest"]

    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key["public_key_hex"])).verify(
        bytes.fromhex(result["demo_signature"]), canonical
    )


def test_owner_signoff_subject_is_loaded_from_verified_manifest(monkeypatch) -> None:
    monkeypatch.setattr(
        portal_app,
        "_git_output",
        lambda _args: "integration/termux-change-sync-policy-20261117",
    )
    response = client.get("/api/owner-signoff-subject")

    assert response.status_code == 200
    result = response.json()
    assert len(result["subject_digest"]) == 64
    assert result["profile_id"] == "CKNEXUS-CORE-v0.1-demo"
    assert result["file_count"] == 11


def test_owner_signoff_subject_rejects_wrong_branch(monkeypatch) -> None:
    monkeypatch.setattr(portal_app, "_git_output", lambda _args: "untrusted-branch")
    response = client.get("/api/owner-signoff-subject")

    assert response.status_code == 503


def test_local_assessment_compile_does_not_write_pycache() -> None:
    from certification_portal.app import ROOT, assess_local

    before = set(ROOT.rglob("*.pyc"))
    assess_local()
    after = set(ROOT.rglob("*.pyc"))

    assert after == before


def test_signoff_form_does_not_prefill_owner_identity() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'name="full_name" required minlength="2" maxlength="160" value=""' in response.text
    assert "somchok naunnin" not in response.text.lower()
