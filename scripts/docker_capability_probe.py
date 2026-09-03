from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass, asdict
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class Check:
    name: str
    status: str
    detail: str
    critical: bool = True


class Probe:
    def __init__(
        self,
        base_url: str,
        token: str,
        webhook_token: str | None,
        expect_mode: str,
        expect_email: bool,
        expect_runtime_binding: bool,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.webhook_token = webhook_token
        self.expect_mode = expect_mode
        self.expect_email = expect_email
        self.expect_runtime_binding = expect_runtime_binding
        self.checks: list[Check] = []
        self.route_count = 0
        self.route_methods = 0
        self.started = time.time()

    def add(self, name: str, ok: bool, detail: str, *, critical: bool = True) -> None:
        self.checks.append(Check(name, "PASS" if ok else "FAIL", detail, critical))

    def request(
        self,
        method: str,
        path: str,
        *,
        body: Any | None = None,
        auth: bool = False,
        webhook: bool = False,
        headers: dict[str, str] | None = None,
        expected: tuple[int, ...] = (200,),
        raw: bool = False,
    ) -> tuple[int, Any, dict[str, str]]:
        request_headers = {"Accept": "application/json"}
        if auth:
            request_headers["Authorization"] = f"Bearer {self.token}"
        if webhook and self.webhook_token:
            request_headers["X-CK-NEXUS-Webhook-Token"] = self.webhook_token
        if headers:
            request_headers.update(headers)
        data = None
        if body is not None and not isinstance(body, bytes):
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        elif isinstance(body, bytes):
            data = body
        request = Request(
            f"{self.base_url}{path}",
            method=method,
            data=data,
            headers=request_headers,
        )
        try:
            with urlopen(request, timeout=15) as response:
                status = response.status
                payload_bytes = response.read()
                response_headers = {k.lower(): v for k, v in response.headers.items()}
        except HTTPError as exc:
            status = exc.code
            payload_bytes = exc.read()
            response_headers = {k.lower(): v for k, v in exc.headers.items()}
        except URLError as exc:
            raise RuntimeError(f"request failed: {method} {path}: {type(exc).__name__}") from exc
        if status not in expected:
            text = payload_bytes.decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"unexpected HTTP {status} for {method} {path}: {text}")
        if raw:
            return status, payload_bytes.decode("utf-8", errors="replace"), response_headers
        content_type = response_headers.get("content-type", "")
        if "json" in content_type and payload_bytes:
            return status, json.loads(payload_bytes), response_headers
        return status, payload_bytes.decode("utf-8", errors="replace"), response_headers

    def safe(self, name: str, fn, *, critical: bool = True) -> Any | None:
        try:
            value, detail = fn()
            self.add(name, True, detail, critical=critical)
            return value
        except Exception as exc:
            self.add(name, False, f"{type(exc).__name__}: {exc}", critical=critical)
            return None

    def run_core(self) -> None:
        def openapi_check():
            _, data, _ = self.request("GET", "/openapi.json")
            paths = data.get("paths", {})
            self.route_count = len(paths)
            self.route_methods = sum(
                1
                for value in paths.values()
                for method in value
                if method.lower() in {"get", "post", "put", "patch", "delete"}
            )
            return data, f"{self.route_count} paths / {self.route_methods} operations discovered"

        self.safe("openapi-route-inventory", openapi_check)

        def health_check():
            _, data, headers = self.request("GET", "/health")
            ok = data.get("status") == "ok"
            if not ok:
                raise RuntimeError(f"health status={data}")
            for key, expected_value in (
                ("x-content-type-options", "nosniff"),
                ("x-frame-options", "DENY"),
                ("referrer-policy", "no-referrer"),
            ):
                if headers.get(key) != expected_value:
                    raise RuntimeError(f"missing/incorrect security header {key}")
            csp = headers.get("content-security-policy", "")
            if "frame-ancestors 'none'" not in csp or "default-src 'self'" not in csp:
                raise RuntimeError("CSP baseline missing")
            return data, "health ok; security headers present"

        self.safe("health-and-security-headers", health_check)

        def live_check():
            _, data, _ = self.request("GET", "/health/live")
            if data.get("live") is not True:
                raise RuntimeError(str(data))
            return data, "liveness true"

        self.safe("liveness", live_check)

        def ready_check():
            _, data, _ = self.request("GET", "/health/ready")
            if data.get("ready") is not True:
                raise RuntimeError(str(data))
            return data, "readiness true"

        self.safe("readiness", ready_check)

        def status_check():
            _, data, _ = self.request("GET", "/api/status")
            if data.get("mode") != self.expect_mode:
                raise RuntimeError(f"expected mode {self.expect_mode}, got {data.get('mode')}")
            if data.get("database_ready") is not True:
                raise RuntimeError("database not ready")
            return data, f"mode={data.get('mode')} database_ready=true"

        self.safe("application-status", status_check)

        def auth_boundary_check():
            status, _, _ = self.request(
                "GET", "/api/control/status", expected=(401,)
            )
            if status != 401:
                raise RuntimeError(f"expected 401, got {status}")
            return status, "protected control endpoint rejects missing token"

        self.safe("control-auth-boundary", auth_boundary_check)

        def control_manifest_check():
            _, data, _ = self.request("GET", "/api/control/manifest", auth=True)
            if not data.get("groups") or int(data.get("route_count", 0)) < 10:
                raise RuntimeError("control manifest missing route inventory")
            return data, f"groups={len(data['groups'])} route_count={data['route_count']}"

        self.safe("control-manifest", control_manifest_check)

        def control_status_check():
            _, data, _ = self.request("GET", "/api/control/status", auth=True)
            binding = bool(data.get("operations", {}).get("runtime_binding_required"))
            if binding != self.expect_runtime_binding:
                raise RuntimeError(
                    f"runtime_binding_required expected {self.expect_runtime_binding}, got {binding}"
                )
            return data, f"environment={data.get('environment')} runtime_binding={binding}"

        self.safe("control-status", control_status_check)

        def agents_check():
            _, data, _ = self.request("GET", "/api/agents", auth=True)
            agents = data.get("agents", [])
            if not agents:
                raise RuntimeError("no agents returned")
            return agents, f"agents={len(agents)}"

        agents = self.safe("agent-catalog", agents_check)
        agent_id = agents[0].get("id") if agents else "script-writer"

        session_id = f"docker-probe-{uuid.uuid4().hex[:10]}"

        def run_check():
            payload = {
                "agent_id": agent_id,
                "prompt": "Summarize CK-NEXUS Docker smoke test in one sentence.",
                "session_id": session_id,
                "audience": "developer",
                "platform": "web",
                "tone": "professional",
                "language": "English",
            }
            _, data, _ = self.request("POST", "/api/runs", body=payload, auth=True)
            if not str(data.get("content", "")).strip():
                raise RuntimeError("empty agent output")
            if data.get("mode") != self.expect_mode:
                raise RuntimeError(f"run mode={data.get('mode')}")
            return data, f"agent={data.get('agent_name')} mode={data.get('mode')}"

        self.safe("agent-execution", run_check)

        def history_check():
            _, data, _ = self.request(
                "GET", f"/api/runs?session_id={session_id}&limit=10", auth=True
            )
            if not isinstance(data, list) or not data:
                raise RuntimeError("run history did not persist")
            return data, f"history rows={len(data)}"

        self.safe("run-history-persistence", history_check)

        def providers_check():
            _, data, _ = self.request("GET", "/api/providers/status", auth=True)
            providers = data.get("providers", [])
            mock = next((p for p in providers if p.get("name") == "mock"), None)
            if self.expect_mode == "mock" and not (mock and mock.get("available")):
                raise RuntimeError(f"mock provider unavailable: {providers}")
            return data, f"providers={len(providers)} preferred={data.get('preferred')}"

        self.safe("provider-router-status", providers_check)

        def credentials_check():
            _, data, _ = self.request("GET", "/api/security/credentials/status", auth=True)
            if data.get("secrets_exposed") is not False:
                raise RuntimeError("credential status exposed secrets flag")
            serialized = json.dumps(data).lower()
            if "sk-" in serialized or "private_key" in serialized:
                raise RuntimeError("credential material pattern appeared in status output")
            return data, "credential status redacted"

        self.safe("credential-redaction", credentials_check)

        def vault_check():
            _, data, _ = self.request("GET", "/api/security/credential-vault/status", auth=True)
            if data.get("secrets_exposed") is not False:
                raise RuntimeError("vault status unsafe")
            return data, f"vault_enabled={data.get('enabled')}"

        self.safe("credential-vault-status", vault_check)

        def integrations_check():
            _, data, _ = self.request("GET", "/api/integrations/status", auth=True)
            if data.get("release_status") != "release_candidate":
                raise RuntimeError(str(data.get("release_status")))
            gate = str(data.get("production_gate", ""))
            if "NO-GO" not in gate:
                raise RuntimeError(f"production gate not truthful: {gate}")
            return data, f"integrations={len(data.get('integrations', []))}; production gate truthful"

        self.safe("integration-hub-status", integrations_check)

        def gmail_status_check():
            _, data, _ = self.request("GET", "/api/integrations/gmail/status", auth=True)
            if "scopes" not in data or "authorized" not in data:
                raise RuntimeError(str(data))
            return data, f"enabled={data.get('enabled')} authorized={data.get('authorized')}"

        self.safe("gmail-oauth-status", gmail_status_check)

        def github_app_check():
            _, data, _ = self.request("GET", "/api/integrations/github-app/status", auth=True)
            return data, f"enabled={data.get('enabled')} configured={data.get('configured')}"

        self.safe("github-app-status", github_app_check, critical=False)

        def metrics_auth_check():
            status, _, _ = self.request("GET", "/metrics", expected=(401,))
            if status != 401:
                raise RuntimeError(f"expected 401 got {status}")
            return status, "metrics protected without token"

        self.safe("metrics-auth-boundary", metrics_auth_check)

        def metrics_check():
            _, text, _ = self.request("GET", "/metrics", auth=True, raw=True)
            if "ckn_build_info" not in text:
                raise RuntimeError("build metric missing")
            return text, f"metrics lines={len(text.splitlines())}"

        self.safe("metrics-output", metrics_check)

        def control_page_check():
            _, text, _ = self.request("GET", "/control", raw=True)
            if "CK-NEXUS" not in text:
                raise RuntimeError("control page missing product identity")
            return text, "control page served"

        self.safe("control-page", control_page_check)

        def connector_disabled_check():
            status, data, _ = self.request(
                "GET", "/api/connectors", auth=True, expected=(503,)
            )
            if status != 503:
                raise RuntimeError(f"expected 503 got {status}")
            text = json.dumps(data)
            if "CONNECTOR_FABRIC_DISABLED" not in text:
                raise RuntimeError(text)
            return data, "connector fabric fails closed when disabled"

        self.safe("connector-disabled-fail-closed", connector_disabled_check)

    def run_email(self) -> None:
        if not self.expect_email:
            return
        if not self.webhook_token:
            self.add("email-suite", False, "webhook token missing")
            return

        def route_check():
            _, data, _ = self.request(
                "POST",
                "/api/email/route",
                body={
                    "matched_alias": "ai@ck-nexus.local",
                    "subject": "CK-NEXUS Docker verification",
                    "sender": "buyer@example.com",
                    "quarantined": False,
                },
                webhook=True,
            )
            if not data.get("category"):
                raise RuntimeError(str(data))
            return data, f"category={data.get('category')} rule={data.get('matched_rule')}"

        self.safe("email-routing", route_check)

        message_id = f"docker-{uuid.uuid4().hex}"

        def ingest_check():
            payload = {
                "mailbox": "admin@ck-nexus.local",
                "provider": "docker-probe",
                "provider_message_id": message_id,
                "internet_message_id": f"<{message_id}@ck-nexus.local>",
                "execution_id": "docker-capability-probe",
            }
            _, first, _ = self.request(
                "POST", "/api/email/ingest", body=payload, webhook=True
            )
            if first.get("status") != "accepted":
                raise RuntimeError(f"first ingest={first}")
            _, second, _ = self.request(
                "POST", "/api/email/ingest", body=payload, webhook=True
            )
            if second.get("status") != "duplicate":
                raise RuntimeError(f"duplicate ingest={second}")
            return first, f"accepted then duplicate; journal={first.get('journal_id')}"

        first = self.safe("email-ingest-dedup", ingest_check)
        if not first:
            return
        journal_id = first.get("journal_id")

        def loop_check():
            _, data, _ = self.request(
                "POST",
                "/api/email/loop-check",
                body={
                    "headers": {"Auto-Submitted": "auto-replied"},
                    "system_addresses": ["admin@ck-nexus.local"],
                },
                webhook=True,
            )
            if data.get("allow_automatic_reply") is not False:
                raise RuntimeError(str(data))
            return data, f"loop prevention reason={data.get('reason')}"

        self.safe("email-loop-prevention", loop_check)

        def attachment_check():
            boundary = f"----cknexus{uuid.uuid4().hex}"
            file_content = b"CK-NEXUS harmless Docker verification attachment\n"
            body = (
                f"--{boundary}\r\n"
                'Content-Disposition: form-data; name="file"; filename="probe.txt"\r\n'
                "Content-Type: text/plain\r\n\r\n"
            ).encode("utf-8") + file_content + f"\r\n--{boundary}--\r\n".encode("utf-8")
            _, data, _ = self.request(
                "POST",
                "/api/email/scan-attachment",
                body=body,
                webhook=True,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            )
            if not data.get("sha256") or int(data.get("size_bytes", 0)) <= 0:
                raise RuntimeError(str(data))
            return data, f"status={data.get('status')} safe={data.get('safe')}"

        self.safe("email-attachment-scan", attachment_check)

        outbox_id: str | None = None

        def outbox_check():
            nonlocal outbox_id
            _, data, _ = self.request(
                "POST",
                "/api/email/outbox",
                body={
                    "journal_id": journal_id,
                    "action_type": "SEND_EMAIL",
                    "destination": "buyer@example.com",
                    "payload": {"subject": "Docker probe", "text": "safe simulated reply"},
                    "deduplication_key": f"docker-probe:{journal_id}:reply",
                },
                webhook=True,
            )
            outbox_id = data.get("outbox_id")
            if not outbox_id:
                raise RuntimeError(str(data))
            return data, f"created={data.get('created')} outbox_id={outbox_id}"

        self.safe("email-outbox-enqueue", outbox_check)
        if not outbox_id:
            return

        def claim_send_check():
            _, claim, _ = self.request(
                "POST",
                "/api/email/outbox/claim",
                body={"worker_id": "docker-probe-worker", "limit": 20, "lease_seconds": 120},
                webhook=True,
            )
            items = claim.get("items", [])
            item = next((item for item in items if item.get("id") == outbox_id), None)
            if item is None:
                raise RuntimeError(f"outbox not claimable: {claim}")
            _, sent, _ = self.request(
                "POST",
                f"/api/email/outbox/{outbox_id}/sent",
                body={"provider_message_id": f"simulated-{uuid.uuid4().hex}"},
                webhook=True,
            )
            if sent.get("status") != "sent":
                raise RuntimeError(str(sent))
            return sent, "outbox claim and simulated sent transition passed"

        self.safe("email-outbox-claim-sent", claim_send_check)

        def audit_check():
            _, data, _ = self.request(
                "GET", f"/api/email/audit/{journal_id}", webhook=True
            )
            events = data.get("events", [])
            if len(events) < 2:
                raise RuntimeError(str(data))
            return data, f"audit events={len(events)}"

        self.safe("email-audit-trace", audit_check)

    def report(self) -> dict[str, Any]:
        critical_failures = [
            check for check in self.checks if check.critical and check.status != "PASS"
        ]
        optional_failures = [
            check for check in self.checks if not check.critical and check.status != "PASS"
        ]
        return {
            "generated_at_unix": time.time(),
            "duration_seconds": round(time.time() - self.started, 3),
            "base_url": self.base_url,
            "expected_mode": self.expect_mode,
            "expected_email": self.expect_email,
            "expected_runtime_binding": self.expect_runtime_binding,
            "openapi_paths": self.route_count,
            "openapi_operations": self.route_methods,
            "checks": [asdict(check) for check in self.checks],
            "summary": {
                "passed": sum(check.status == "PASS" for check in self.checks),
                "failed": sum(check.status != "PASS" for check in self.checks),
                "critical_failures": len(critical_failures),
                "optional_failures": len(optional_failures),
                "overall": "PASS" if not critical_failures else "FAIL",
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:18000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--webhook-token")
    parser.add_argument("--expect-mode", default="mock")
    parser.add_argument("--expect-email", action="store_true")
    parser.add_argument("--expect-runtime-binding", action="store_true")
    parser.add_argument("--report", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    probe = Probe(
        args.base_url,
        args.token,
        args.webhook_token,
        args.expect_mode,
        args.expect_email,
        args.expect_runtime_binding,
    )
    probe.run_core()
    probe.run_email()
    report = probe.report()
    with open(args.report, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    for check in probe.checks:
        print(f"[{check.status}] {check.name}: {check.detail}")
    print(json.dumps(report["summary"], indent=2))
    return 0 if report["summary"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
