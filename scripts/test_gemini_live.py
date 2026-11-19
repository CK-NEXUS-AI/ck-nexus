from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main() -> int:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("Q11 GEMINI BLOCKED: GEMINI_API_KEY is not configured")
        return 2

    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()
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
        with urlopen(request, timeout=45) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        # Report only Google's structured status; never print headers, URL, or key.
        google_status = "UNKNOWN"
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            google_status = str((error_body.get("error") or {}).get("status") or "UNKNOWN")
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            pass
        print(f"Q11 GEMINI FAIL: http_status={exc.code} google_status={google_status}")
        return 1
    except (URLError, TimeoutError, OSError) as exc:
        print(f"Q11 GEMINI FAIL: transport_error={type(exc).__name__}")
        return 1
    except (ValueError, KeyError) as exc:
        print(f"Q11 GEMINI FAIL: response_error={type(exc).__name__}")
        return 1

    candidates = body.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
    output = "".join(str(part.get("text") or "") for part in parts).strip()
    if output != "CK-NEXUS-GEMINI-LIVE-PASS":
        print("Q11 GEMINI FAIL: expected sentinel not returned")
        return 1
    print(f"Q11 GEMINI PASS model={model} sentinel=observed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
