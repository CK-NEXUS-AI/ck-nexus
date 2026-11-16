"""Regression tests for the read-only certification assessment prototype."""

import hashlib
import json

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi.testclient import TestClient

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
        check["control"] == "CKN-GOV-001_POLICY_ADOPTION"
        and check["result"] == "FAIL"
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
    canonical = json.dumps(
        signed_body, sort_keys=True, separators=(",", ":")
    ).encode()
    assert hashlib.sha256(canonical).hexdigest() == result["digest"]

    Ed25519PublicKey.from_public_bytes(bytes.fromhex(key["public_key_hex"])).verify(
        bytes.fromhex(result["demo_signature"]), canonical
    )
