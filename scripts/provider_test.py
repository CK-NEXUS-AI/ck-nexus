#!/usr/bin/env python3
"""CK-NEXUS Provider Auto-Test — scan keys, validate, route a test prompt."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Ensure creator_app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from creator_app.free_providers import QuotaTracker, build_free_adapters
from creator_app.provider_registry import PROVIDER_REGISTRY


def scan_keys() -> list[dict]:
    """Scan environment for all known provider API keys."""
    results = []
    for spec in PROVIDER_REGISTRY:
        key = os.environ.get(spec.env_key, "").strip()
        results.append(
            {
                "name": spec.name,
                "slug": spec.slug,
                "icon": spec.icon,
                "tier": spec.tier,
                "env_key": spec.env_key,
                "has_key": bool(key),
                "key_preview": (f"****{key[-4:]}" if len(key) > 8 else ("***" if key else None)),
                "free_models": list(spec.free_models),
            }
        )
    return results


def print_scan(scan: list[dict]) -> int:
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║       CK-NEXUS Multi-Provider Key Scanner          ║")
    print("╚══════════════════════════════════════════════════════╝\n")
    found = 0
    for provider in scan:
        status = "✅" if provider["has_key"] else "❌"
        tier_tag = "FREE" if provider["tier"] == "free" else "FREEMIUM"
        models = ", ".join(provider["free_models"][:2]) if provider["free_models"] else "-"
        print(
            f"  {status} {provider['icon']}  {provider['name']:<16} "
            f"[{tier_tag}]  {provider['env_key']}"
        )
        if provider["has_key"]:
            found += 1
            print(f"     key: {provider['key_preview']}   models: {models}")
    print(f"\n  📊 Found {found}/{len(scan)} configured providers\n")
    return found


async def test_routing() -> None:
    """Try routing a test prompt through available free providers."""
    qt = QuotaTracker()
    adapters = build_free_adapters(quota_tracker=qt)

    if not adapters:
        print("  ⚠️  No free provider keys found. Set at least one:")
        print("     export GROQ_API_KEY=gsk_...")
        print("     export GEMINI_API_KEY=AIza...")
        print("     export DEEPSEEK_API_KEY=sk-...")
        print("     export OPENROUTER_API_KEY=sk-or-...")
        return

    provider_names = ", ".join(adapter.name for adapter in adapters)
    print(f"  🔀 Found {len(adapters)} free provider(s): {provider_names}\n")

    test_prompt = "Say hello in one sentence."
    results = []

    for adapter in adapters:
        if not adapter.is_available():
            print(f"  ⏭️  {adapter.name}: skipped (not available)")
            continue

        print(f"  🚀 Testing {adapter.name} ({adapter.model})...")
        start = time.monotonic()
        try:
            output = await adapter.invoke(test_prompt)
            elapsed = time.monotonic() - start
            results.append(
                {
                    "provider": adapter.name,
                    "ok": True,
                    "time": elapsed,
                    "output": output[:120],
                }
            )
            print(f"     ✅ {elapsed:.1f}s — {output[:100]}...")
        except Exception as exc:
            elapsed = time.monotonic() - start
            err_msg = str(exc)[:100]
            results.append(
                {
                    "provider": adapter.name,
                    "ok": False,
                    "time": elapsed,
                    "error": err_msg,
                }
            )
            print(f"     ❌ {elapsed:.1f}s — {err_msg}")

    # Summary
    ok_count = sum(1 for result in results if result["ok"])
    print(f"\n  📊 Results: {ok_count}/{len(results)} providers responded successfully")
    if ok_count > 0:
        fastest = min(
            (result for result in results if result["ok"]),
            key=lambda result: result["time"],
        )
        print(f"  ⚡ Fastest: {fastest['provider']} ({fastest['time']:.1f}s)")

    # Quota stats
    print("\n  📈 Quota Stats:")
    for adapter in adapters:
        stats = qt.stats(adapter.name)
        if stats["requests"] > 0 or stats["rate_limited"]:
            print(
                f"     {adapter.name}: {stats['requests']} reqs, "
                f"{stats['tokens']} tokens, "
                f"rate_limited={stats['rate_limited']}"
            )


def main() -> None:
    print("\n🔄 CK-NEXUS Provider Auto-Test\n")

    # Step 1: Scan keys
    scan = scan_keys()
    found = print_scan(scan)

    if found == 0:
        print("  💡 To get started, sign up for free tiers:")
        print("     ⚡ Groq:        https://console.groq.com/keys")
        print("     💎 Gemini:      https://aistudio.google.com/apikey")
        print("     🔍 DeepSeek:    https://platform.deepseek.com/")
        print("     🔀 OpenRouter:  https://openrouter.ai/keys")
        print("     🧠 Cerebras:    https://cloud.cerebras.ai/")
        print("     🤝 Together:    https://api.together.xyz/settings/api-keys")
        print("     🌊 Mistral:     https://console.mistral.ai/api-keys/")
        print("     🤗 HuggingFace: https://huggingface.co/settings/tokens")
        print()
        return

    # Step 2: Test routing
    print("─" * 56)
    asyncio.run(test_routing())
    print("─" * 56)
    print("\n✅ Provider auto-test complete.\n")


if __name__ == "__main__":
    main()
