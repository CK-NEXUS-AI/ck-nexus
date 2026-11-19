from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> int:
    model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    result = {
        "schema_version": 1,
        "gate": "Q11_GEMINI_LIVE",
        "provider": "gemini",
        "model": model,
        "checked_at": datetime.now(UTC).isoformat(),
        "result": "BLOCKED",
        "credential_configured": bool(api_key),
        "sentinel_observed": False,
        "diagnostic": "not executed",
    }
    if not api_key:
        result["diagnostic"] = "GEMINI_API_KEY is not configured"
        return write_result(result, 2)

    payload = {
        "contents": [{
            "role": "user",
            "parts": [{
                "text": "Reply with exactly this token and nothing else: CK-NEXUS-GEMINI-LIVE-PASS"
            }],
        }],
        "generationConfig": {"maxOutputTokens": 32, "temperature": 0},
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    try:
        with urlopen(request, timeout=90) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        result["result"] = "FAIL"
        result["http_status"] = exc.code
        result["diagnostic"] = f"Gemini API returned HTTP {exc.code}"
        return write_result(result, 1)
    except Exception as exc:
        result["result"] = "FAIL"
        result["diagnostic"] = f"request failed ({type(exc).__name__})"
        return write_result(result, 1)

    candidates = body.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    output = "".join(str(part.get("text") or "") for part in parts).strip()
    if output != "CK-NEXUS-GEMINI-LIVE-PASS":
        result["result"] = "FAIL"
        result["diagnostic"] = "expected response sentinel was not returned"
        return write_result(result, 1)

    result["result"] = "PASS"
    result["sentinel_observed"] = True
    result["diagnostic"] = "Gemini API returned the expected sentinel"
    return write_result(result, 0)


def write_result(result: dict[str, object], exit_code: int) -> int:
    path = Path(os.getenv("GEMINI_EVIDENCE_PATH", "gemini-live-evidence.json"))
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"{result['gate']} {result['result']} "
        f"provider={result['provider']} model={result['model']}"
    )
    print(f"evidence_path={path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
