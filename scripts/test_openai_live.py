from __future__ import annotations

import os

EXIT_VERIFIED = 0
EXIT_BLOCKED_PROVIDER_QUOTA = 10
EXIT_BLOCKED_PROVIDER_AUTH = 11
EXIT_BLOCKED_PROVIDER_NETWORK = 12
EXIT_DEFECT_RUNTIME = 40
EXIT_DEFECT_EVIDENCE = 41
EXIT_UNKNOWN = 99


def _safe_error_metadata(exc: BaseException) -> tuple[int | None, str | None]:
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int):
        status = None
    body = getattr(exc, "body", None)
    code = body.get("code") if isinstance(body, dict) else None
    return status, code if isinstance(code, str) else None


def classify_exception(exc: BaseException) -> tuple[int, str, int | None, str | None]:
    status, code = _safe_error_metadata(exc)
    if code == "insufficient_quota" or status == 429:
        return EXIT_BLOCKED_PROVIDER_QUOTA, "BLOCKED_PROVIDER_QUOTA", status, code
    if status in {401, 403}:
        return EXIT_BLOCKED_PROVIDER_AUTH, "BLOCKED_PROVIDER_AUTH", status, code
    try:
        from openai import APIConnectionError, APITimeoutError
    except ImportError:
        APITimeoutError = APIConnectionError = None
    network_types = tuple(
        cls for cls in (APITimeoutError, APIConnectionError) if cls is not None
    )
    if network_types and isinstance(exc, network_types):
        return EXIT_BLOCKED_PROVIDER_NETWORK, "BLOCKED_PROVIDER_NETWORK", status, code
    return EXIT_UNKNOWN, "UNKNOWN", status, code


def main() -> int:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("P0-AI-001 BLOCKED: credential not configured")
        return EXIT_DEFECT_RUNTIME

    try:
        from openai import OpenAI
    except ImportError:
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
            print("P0-AI-001 FAIL: expected sentinel missing")
            return EXIT_UNKNOWN
        print(f"P0-AI-001 PASS model={model} response_id={response.id}")
        print(output)
        return EXIT_VERIFIED
    except Exception as exc:
        exit_code, classification, status, code = classify_exception(exc)
        print(f"P0-AI-001 {classification} status={status} code={code}")
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
