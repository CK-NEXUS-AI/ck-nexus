#!/usr/bin/env python3
"""Ingest API Key — วาง key แล้วเก็บใน vault อัตโนมัติ.

วิธีใช้:
    # วาง key ตรงๆ
    python scripts/ingest_key.py "PMAK-xxxxx"

    # อ่านจากไฟล์
    python scripts/ingest_key.py --file keys.txt

    # ดูรายการ key ที่เก็บไว้
    python scripts/ingest_key.py --list

    # เชื่อมต่อกับ provider
    python scripts/ingest_key.py --connect postman
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from creator_app.credentials.blind_vault import BlindVault, scan_and_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Blind Key Ingestion")
    parser.add_argument("key", nargs="?", help="API key ที่ต้องการเก็บ")
    parser.add_argument("--provider", "-p", help="Provider name (auto-detect if omitted)")
    parser.add_argument("--file", "-f", help="อ่าน key จากไฟล์")
    parser.add_argument("--list", "-l", action="store_true", help="ดูรายการ key ที่เก็บไว้")
    parser.add_argument("--connect", "-c", help="เชื่อมต่อกับ provider")
    parser.add_argument("--status", "-s", action="store_true", help="สถานะ vault")
    args = parser.parse_args()

    vault = BlindVault()

    if args.list:
        entries = vault.list_entries()
        if not entries:
            print("Vault ว่าง — ยังไม่มี key ที่เก็บไว้")
            return
        print(f"📦 Vault: {len(entries)} keys\n")
        for e in entries:
            print(f"  {e['vault_id']}")
            print(f"    Provider: {e['provider']}")
            print(f"    Hash: {e['key_hash']}")
            print(f"    Created: {e['created_at'][:19]}")
            if e['use_count'] > 0:
                print(f"    Used: {e['use_count']}x")
            print()
        return

    if args.status:
        status = vault.status()
        print("📦 Vault Status")
        print(f"   Total keys: {status['total_keys']}")
        print(f"   Providers: {status['providers']}")
        print(f"   Dir: {status['vault_dir']}")
        return

    if args.connect:
        provider = args.connect
        entries = vault.list_entries(provider=provider)
        if not entries:
            print(f"❌ ไม่พบ key สำหรับ {provider} ใน vault")
            print(f"   เก็บ key ก่อน: python ingest_key.py \"YOUR_KEY\" -p {provider}")
            return
        vid = entries[0]["vault_id"]
        key = vault.retrieve(vid)
        print(f"🔑 {provider}: vault_id={vid}")
        print(f"   Key retrieved (length={len(key)} chars)")
        print("   Ready to use!")
        return

    if args.key:
        results = scan_and_store(args.key, vault)
        if not results:
            print("❌ ไม่พบ API key ที่รู้จักในข้อความ")
            return
        print("✅ เก็บ key สำเร็จ (agent ไม่เห็นค่าจริง)\n")
        for r in results:
            status_icon = "📦" if r["status"] == "stored" else "♻️"
            print(f"  {status_icon} {r['provider']}: {r['vault_id']}")
        return

    if args.file:
        content = Path(args.file).read_text()
        results = scan_and_store(content, vault)
        if not results:
            print("❌ ไม่พบ API key ที่รู้จักในไฟล์")
            return
        print(f"✅ เก็บ {len(results)} keys จากไฟล์\n")
        for r in results:
            status_icon = "📦" if r["status"] == "stored" else "♻️"
            print(f"  {status_icon} {r['provider']}: {r['vault_id']}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
