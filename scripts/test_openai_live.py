from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

EXIT_VERIFIED = 0
EXIT_BLOCKED_PROVIDER_QUOTA = 10
EXIT_BLOCKED_PROVIDER_AUTH = 11
EXIT_BLOCKED_PROVIDER_NETWORK = 12
EXIT_DEFECT_RUNTIME = 40
EXIT_DEFECT_EVIDENCE = 41
EXIT_UNKNOWN = 99


def _source_identity() -> str:
    configured = os.getenv("Q11_SOURCE_IDENTITY", "").strip()
    if configured:
        return configured
    try:
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.SubprocessError):
        sha = "unknown"
    return f"git:{sha}"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_error_metadata(
    exc: BaseException,
) -> tuple[int | None, str | None, str | None, str | None]:
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = None
    body = getattr(exc, "body", None)
    code = body.get("code") if isinstance(body, dict) else None
    error_type = body.get("type") if isinstance(body, dict) else None
    request_id = getattr(exc, "request_id", None)
    if not isinstance(request_id, str) or not request_id:
        request_id = None
    code = code[:128] if isinstance(code, str) else None
    error_type = error_type[:128] if isinstance(error_type, str) else None
    return status, code, error_type, request_id


def _redacted_response_body(
    status: int | None, code: str | None, error_type: str | None
) -> bytes:
    payload = {"http_status": status, "provider_code": code, "provider_type": error_type}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def classify_exception(
    exc: BaseException,
) -> tuple[int, str, int | None, str | None, str | None]:
    status, code, error_type, request_id = _safe_error_metadata(exc)
    if code == "insufficient_quota" or status == 429:
        return EXIT_BLOCKED_PROVIDER_QUOTA, "BLOCKED_PROVIDER_QUOTA", status, code, request_id
    if status in {401, 403}:
        return EXIT_BLOCKED_PROVIDER_AUTH, "BLOCKED_PROVIDER_AUTH", status, code, request_id
    try:
        from openai import APIConnectionError, APITimeoutError
    except ImportError:
        APITimeoutError = APIConnectionError = None
    network_types = tuple(
        cls for cls in (APITimeoutError, APIConnectionError) if cls is not None
    )
    if network_types and isinstance(exc, network_types):
        return EXIT_BLOCKED_PROVIDER_NETWORK, "BLOCKED_PROVIDER_NETWORK", status, code, request_id
    return EXIT_UNKNOWN, "UNKNOWN", status, code, request_id


def emit_evidence(
    *,
    classification: str,
    exit_code: int,
    http_status: int | None = None,
    provider_code: str | None = None,
    request_id: str | None = None,
    response_body_sha256: str | None = None,
) -> Path:
    captured_at = _utc_now()
    payload = {
        "gate": "Q11-F",
        "classification": classification,
        "exit_code": exit_code,
        "provider": "openai",
        "endpoint": "responses.create",
        "http_status": http_status,
        "provider_code": provider_code,
        "request_id": request_id,
        "response_body_sha256": response_body_sha256,
        "response_body_redacted": True,
        "captured_at": captured_at,
        "source_identity": _source_identity(),
        "secret_exposed": False,
        "promotion_blocked": exit_code != EXIT_VERIFIED,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["canonical_digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
    artifact = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    digest = hashlib.sha256(artifact).hexdigest()
    directory = Path(os.getenv("Q11_EVIDENCE_DIR", "evidence/automation"))
    directory.mkdir(parents=True, exist_ok=True)
    stamp = captured_at.replace(":", "").replace("-", "")
    path = directory / f"q11-p02-error-classification-{stamp}.json"
    path.write_bytes(artifact)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return path


def main() -> int:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        try:
            emit_evidence(classification="DEFECT_RUNTIME", exit_code=EXIT_DEFECT_RUNTIME)
        except Exception:
            return EXIT_DEFECT_EVIDENCE
        print("P0-AI-001 BLOCKED: credential not configured")
        return EXIT_DEFECT_RUNTIME

    try:
        from openai import OpenAI
    except ImportError:
        try:
            emit_evidence(classification="DEFECT_RUNTIME", exit_code=EXIT_DEFECT_RUNTIME)
        except Exception:
            return EXIT_DEFECT_EVIDENCE
        print("P0-AI-001 BLOCKED: OpenAI SDK unavailable")
        return EXIT_DEFECT_RUNTIME

    model = os.getenv("OPENAI_SMOKE_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    try:
        client = OpenAI()
        response = client.responses.create(
            model=model,
            input=(
                "Return exactly one line in Thai that contains the token "
                "CK-NEXUS-P0-SMOKE-PASS and states that the production smoke test passed."
            ),
            max_output_tokens=64,
        )
        output = response.output_text.strip()
        if "CK-NEXUS-P0-SMOKE-PASS" not in output:
            try:
                emit_evidence(classification="UNKNOWN", exit_code=EXIT_UNKNOWN)
            except Exception:
                return EXIT_DEFECT_EVIDENCE
            print("P0-AI-001 FAIL: expected sentinel missing")
            return EXIT_UNKNOWN
        try:
            emit_evidence(classification="VERIFIED", exit_code=EXIT_VERIFIED)
        except Exception:
            return EXIT_DEFECT_EVIDENCE
        print(f"P0-AI-001 PASS model={model} response_id={response.id}")
        print(output)
        return EXIT_VERIFIED
    except Exception as exc:
        exit_code, classification, status, code, request_id = classify_exception(exc)
        body_hash = hashlib.sha256(_redacted_response_body(status, code, None)).hexdigest()
        try:
            emit_evidence(
                classification=classification,
                exit_code=exit_code,
                http_status=status,
                provider_code=code,
                request_id=request_id,
                response_body_sha256=body_hash,
            )
        except Exception:
            return EXIT_DEFECT_EVIDENCE
        print(f"P0-AI-001 {classification} status={status} code={code}")
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
