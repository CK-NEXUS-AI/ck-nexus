#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

SENTINEL = "CK-NEXUS-P0-SMOKE-PASS"


def request_json(url: str, api_key: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = response.read()
            return response.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Never print response bodies or request headers; they may contain sensitive data.
        return exc.code, {}
    except Exception:
        return 0, {}


def main() -> int:
    provider = os.getenv("PROVIDER", "openai").strip().lower()
    if provider not in {"openai", "groq", "openrouter"}:
        print("P0-AI-001 BLOCKED: unsupported provider")
        return 2

    key_names = {
        "openai": "OPENAI_API_KEY",
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    api_key = os.getenv(key_names[provider], "").strip()
    if not api_key:
        print(f"P0-AI-001 BLOCKED: {key_names[provider]} is not configured")
        return 2

    prompt = (
        "Return exactly one line containing the token "
        + SENTINEL
        + ". Do not omit or alter the token."
    )

    if provider == "openai":
        model = os.getenv("OPENAI_SMOKE_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        url = "https://api.openai.com/v1/responses"
        payload = {
            "model": model,
            "input": prompt,
            "max_output_tokens": 64,
        }
    else:
        defaults = {
            "groq": "llama-3.3-70b-versatile",
            "openrouter": "google/gemini-2.0-flash-exp:free",
        }
        base_urls = {
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }
        model = os.getenv("SMOKE_MODEL", defaults[provider])
        url = base_urls[provider].rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 64,
            "temperature": 0,
        }

    status, body = request_json(url, api_key, payload)
    if status != 200:
        print(f"P0-AI-001 BLOCKED: provider HTTP status {status or 'NETWORK_ERROR'}")
        return 2

    response_id = str(body.get("id", "unknown"))
    if provider == "openai":
        output = body.get("output_text", "")
        if not output:
            chunks = []
            for item in body.get("output", []):
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        chunks.append(content.get("text", ""))
            output = "\n".join(chunks)
    else:
        choices = body.get("choices", [])
        output = ""
        if choices:
            output = choices[0].get("message", {}).get("content", "")
            if isinstance(output, list):
                output = " ".join(
                    part.get("text", "") for part in output if isinstance(part, dict)
                )

    if SENTINEL not in str(output):
        print("P0-AI-001 FAIL: expected sentinel missing")
        return 1

    print(
        f"P0-AI-001 PASS provider={provider} model={model} "
        f"response_id={response_id} sentinel_observed=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
