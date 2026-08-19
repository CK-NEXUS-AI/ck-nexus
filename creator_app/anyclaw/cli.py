#!/usr/bin/env python3
"""AnyClaw CLI — Terminal Chat Interface.

วิธีใช้:
    python -m creator_app.anyclaw.cli --chat "สวัสดี"
    python -m creator_app.anyclaw.cli --chat "เขียนโค้ด" --mode super
    python -m creator_app.anyclaw.cli --status
    python -m creator_app.anyclaw.cli --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from creator_app.anyclaw.core import AnyClawCore


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AnyClaw Super-Intelligent Terminal Chat",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m creator_app.anyclaw.cli --chat "สวัสดี"
  python -m creator_app.anyclaw.cli --chat "เขียน Python" --mode super
  python -m creator_app.anyclaw.cli --chat "วิเคราะห์ข้อมูล" --mode free
  python -m creator_app.anyclaw.cli --status
  python -m creator_app.anyclaw.cli --interactive
        """,
    )
    parser.add_argument("--chat", "-c", help="ข้อความที่ต้องการส่ง")
    parser.add_argument(
        "--mode", "-m",
        choices=["super", "free", "claude"],
        default="super",
        help="โหมด: super (free→claude), free (free only), claude (claude only)",
    )
    parser.add_argument("--status", "-s", action="store_true", help="ดูสถานะระบบ")
    parser.add_argument("--interactive", "-i", action="store_true", help="โหมดแชทต่อเนื่อง")
    parser.add_argument("--clear-cache", action="store_true", help="ล้างแคช")
    args = parser.parse_args()

    claw = AnyClawCore(mode=args.mode)

    if args.status:
        status = claw.status()
        print("╔══════════════════════════════════════════╗")
        print("║  🤖 AnyClaw Status                       ║")
        print("╚══════════════════════════════════════════╝")
        print(f"  Mode: {status['mode']}")
        print(f"  Cache: {status['cache_size']} entries")
        print(f"  Total chats: {status['total_chats']}")
        print(f"  Free providers: {', '.join(status['free_providers_available']) or 'none'}")
        print(f"  Claude: {'✅' if status['claude_available'] else '❌'}")
        if status["calls_by_provider"]:
            print("  Calls by provider:")
            for prov, count in status["calls_by_provider"].items():
                print(f"    {prov}: {count}")
        return

    if args.clear_cache:
        claw.clear_cache()
        print("✅ Cache cleared")
        return

    if args.interactive:
        print("╔══════════════════════════════════════════╗")
        print("║  🤖 AnyClaw Interactive Chat             ║")
        print("║  พิมพ์ 'quit' หรือ 'exit' เพื่อออก       ║")
        print(f"║  Mode: {args.mode}                           ║")
        print("╚══════════════════════════════════════════╝")
        print()
        while True:
            try:
                user_input = input("🧑 You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ("quit", "exit", "q"):
                    print("👋 ลาก่อน!")
                    break
                resp = claw.chat(user_input)
                provider_icon = {
                    "cache": "⚡", "groq": "🟢", "openrouter_free": "🟢",
                    "google_ai": "🔵", "ollama_local": "🟣", "claude": "🟠",
                }.get(resp.provider, "⚪")
                print(f"\n{provider_icon} {resp.provider}: {resp.content}")
                print(f"   ({resp.latency_ms:.0f}ms)\n")
            except (KeyboardInterrupt, EOFError):
                print("\n👋 ลาก่อน!")
                break
        return

    if args.chat:
        resp = claw.chat(args.chat)
        provider_icon = {
            "cache": "⚡", "groq": "🟢", "openrouter_free": "🟢",
            "google_ai": "🔵", "ollama_local": "🟣", "claude": "🟠",
        }.get(resp.provider, "⚪")
        print(f"{provider_icon} [{resp.provider}] {resp.content}")
        print(f"   ⏱️ {resp.latency_ms:.0f}ms | model: {resp.model}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
