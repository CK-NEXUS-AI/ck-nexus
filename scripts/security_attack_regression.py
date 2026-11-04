from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from creator_app.connector_fabric.security import (
    EndpointPolicy,
    EndpointSecurityError,
    validate_endpoint,
)
from creator_app.credential_broker import (
    CredentialAccessDenied,
    CredentialBroker,
    CredentialId,
)
from creator_app.gmail_governance.attachments import evaluate_attachment
from creator_app.gmail_oauth import GmailOAuthError, OAuthStateStore

BASE_URL = os.getenv("CKNEXUS_SECURITY_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ACCESS_TOKEN = os.getenv("CKNEXUS_SECURITY_ACCESS_TOKEN", "test-access-value")
EVIDENCE_PATH = Path(
    os.getenv("CKNEXUS_SECURITY_EVIDENCE", "security-attack-regression.json")
)
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def check(name: str, condition: bool, details: str = "") -> dict[str, object]:
    return {"name": name, "passed": bool(condition), "details": details}


def _validate_test_target() -> None:
    parsed = urlsplit(BASE_URL)
    if parsed.scheme != "http" or parsed.hostname not in _LOOPBACK_HOSTS:
        raise RuntimeError("Security regression target must be an HTTP loopback endpoint.")
    if parsed.username is not None or parsed.password is not None:
        raise RuntimeError("Security regression target must not contain URL credentials.")


def request(
    path: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    auth: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    headers: dict[str, str] = {}
    if auth:
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(f"{BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        # The target is constrained by _validate_test_target() to this CI job's loopback.
        with urlopen(req, timeout=5) as response:  # nosec B310
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()


def wait_ready() -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            status, _, _ = request("/api/integrations/gmail/status")
            if status in {200, 401, 503}:
                return
        except OSError:
            pass
        time.sleep(0.5)
    raise RuntimeError("CK-NEXUS local runtime did not become ready")


def main() -> int:
    _validate_test_target()
    wait_ready()
    results: list[dict[str, object]] = []

    status, _, _ = request("/api/integrations/gmail/status")
    results.append(
        check(
            "protected_route_rejects_unauthenticated",
            status == 401,
            f"status={status}",
        )
    )

    status, headers, body = request("/api/integrations/gmail/status", auth=True)
    decoded = body.decode("utf-8", errors="replace")
    results.append(
        check("protected_route_accepts_valid_bearer", status == 200, f"status={status}")
    )
    lowered = decoded.lower()
    results.append(
        check(
            "gmail_status_does_not_expose_secret_fields",
            all(
                term not in lowered
                for term in ("access_token", "refresh_token", "client_secret")
            ),
        )
    )
    normalized_headers = {key.lower(): value for key, value in headers.items()}
    results.append(
        check(
            "header_nosniff",
            normalized_headers.get("x-content-type-options") == "nosniff",
        )
    )
    results.append(
        check(
            "header_frame_deny",
            normalized_headers.get("x-frame-options") == "DENY",
        )
    )
    results.append(
        check(
            "header_referrer_policy",
            normalized_headers.get("referrer-policy") == "no-referrer",
        )
    )
    results.append(
        check(
            "header_csp_present",
            bool(normalized_headers.get("content-security-policy")),
        )
    )

    oversized = b"{\"x\":\"" + (b"A" * 70_000) + b"\"}"
    status, _, _ = request("/api/run", method="POST", body=oversized, auth=True)
    results.append(check("oversized_request_blocked", status == 413, f"status={status}"))

    blocked_addresses = ("127.0.0.1", "169.254.169.254", "10.0.0.8", "::1")
    for address in blocked_addresses:
        try:
            validate_endpoint(
                "https://connector.example/mcp",
                resolver=lambda _host, address=address: (address,),
            )
        except EndpointSecurityError:
            passed = True
        else:
            passed = False
        results.append(check(f"ssrf_rejects_{address.replace(':', '_')}", passed))

    try:
        validate_endpoint(
            "http://127.0.0.1:9000/mcp",
            policy=EndpointPolicy(allow_private_network=True),
            resolver=lambda _host: ("127.0.0.1",),
        )
    except EndpointSecurityError:
        private_allowed = False
    else:
        private_allowed = True
    results.append(check("private_network_requires_explicit_policy", private_allowed))

    state_store = OAuthStateStore(ttl_seconds=60)
    state = state_store.issue()
    state_store.consume(state)
    try:
        state_store.consume(state)
    except GmailOAuthError:
        replay_blocked = True
    else:
        replay_blocked = False
    results.append(check("oauth_state_replay_blocked", replay_blocked))

    broker = CredentialBroker()
    test_credential = "test-credential-value"
    broker.put_ephemeral(
        CredentialId.GMAIL_ACCESS_TOKEN,
        test_credential,
        source="test",
    )
    lease = broker.acquire(CredentialId.GMAIL_ACCESS_TOKEN, consumer="gmail.api")
    results.append(
        check("secret_lease_repr_redacted", test_credential not in repr(lease))
    )
    try:
        lease.reveal(consumer="gmail.oauth")
    except CredentialAccessDenied:
        wrong_consumer_blocked = True
    else:
        wrong_consumer_blocked = False
    results.append(check("secret_lease_consumer_binding", wrong_consumer_blocked))

    executable = evaluate_attachment("invoice.exe", size_bytes=128)
    traversal = evaluate_attachment("../invoice.pdf", size_bytes=128)
    normal_pdf = evaluate_attachment(
        "invoice.pdf", size_bytes=128, head=b"%PDF-1.7\n"
    )
    renamed_executable = evaluate_attachment(
        "invoice.pdf", size_bytes=128, head=b"MZ\x90\x00"
    )
    mismatched_document = evaluate_attachment(
        "invoice.docx", size_bytes=128, head=b"%PDF-1.7\n"
    )
    results.append(
        check(
            "attachment_executable_blocked",
            not executable.allowed_for_parser_sandbox,
        )
    )
    results.append(
        check(
            "attachment_traversal_blocked",
            not traversal.allowed_for_parser_sandbox,
        )
    )
    results.append(
        check(
            "attachment_pdf_signature_validated",
            normal_pdf.allowed_for_parser_sandbox,
        )
    )
    results.append(
        check(
            "attachment_renamed_executable_rejected",
            not renamed_executable.allowed_for_parser_sandbox
            and renamed_executable.reason == "content_signature_mismatch",
        )
    )
    results.append(
        check(
            "attachment_mismatched_document_rejected",
            not mismatched_document.allowed_for_parser_sandbox
            and mismatched_document.reason == "content_signature_mismatch",
        )
    )
    results.append(
        check(
            "attachment_allowed_file_still_quarantined",
            normal_pdf.allowed_for_parser_sandbox
            and normal_pdf.quarantine_required
            and not normal_pdf.execute_on_host,
        )
    )

    issue_references = [
        {"issue": 65, "title": "Security: prevent DNS-rebinding/TOCTOU SSRF in dynamic connector transport"},
        {"issue": 66, "title": "Security hardening: validate attachment content/magic before parser sandbox"},
    ]

    passed = sum(1 for item in results if item["passed"])
    failed = len(results) - passed
    evidence = {
        "schema_version": 1,
        "suite": "CK-NEXUS Security Attack Regression V1",
        "base_url": BASE_URL,
        "tests_total": len(results),
        "tests_passed": passed,
        "tests_failed": failed,
        "results": results,
        "issue_references": issue_references,
        "release_evidence": False,
        "production_promotion": False,
    }
    EVIDENCE_PATH.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
