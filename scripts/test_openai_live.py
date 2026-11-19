from __future__ import annotations

import os


def main() -> int:
    if not os.getenv("OPENAI_API_KEY", "").strip():
        print("P0-AI-001 BLOCKED: OPENAI_API_KEY is not configured")
        return 2

    try:
        from openai import OpenAI
    except ImportError as exc:
        print(f"P0-AI-001 BLOCKED: OpenAI SDK unavailable: {exc}")
        return 2

    model = os.getenv("OPENAI_SMOKE_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini"))
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
        print(output[:500])
        return 1
    print(f"P0-AI-001 PASS model={model} response_id={response.id}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
