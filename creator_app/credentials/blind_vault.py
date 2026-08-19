"""Blind Vault — ระบบเก็บ API Key แบบตาบอด.

หลักการ: Agent เห็นแค่ vault_id ไม่เห็นค่าจริง
- User วาง key ใน input (ไม่ใช่แชทกับ agent)
- Script จับ key → เข้ารหัส → เก็บใน vault
- Agent code ดึง key จาก vault ด้วย vault_id
- ไม่มีทางที่ key จะหลุดออกมาใน output

วิธีใช้:
    # เก็บ key
    vault = BlindVault()
    vid = vault.store("postman", "PMAK-xxxxx")
    print(f"เก็บแล้ว: {vid}")  # agent เห็นแค่นี้

    # ดึง key (เฉพาะตอนใช้งานจริง)
    key = vault.retrieve(vid)
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import secrets
from dataclasses import dataclass
from pathlib import Path

# ─── Key Patterns — จับ API key รูปแบบต่างๆ ────────────────

KEY_PATTERNS: dict[str, re.Pattern] = {
    "postman": re.compile(r"PMAK-[a-zA-Z0-9]{20,}"),
    "openai": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    "anthropic": re.compile(r"sk-ant-[a-zA-Z0-9\-]{20,}"),
    "openrouter": re.compile(r"sk-or-v1-[a-zA-Z0-9]{20,}"),
    "groq": re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
    "google_ai": re.compile(r"AIza[a-zA-Z0-9\-_]{20,}"),
    "github": re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    "github_app": re.compile(r"(ghu|ghs)_[a-zA-Z0-9]{20,}"),
    "telegram_bot": re.compile(r"\d{8,}:[A-Za-z0-9\-_]{20,}"),
    "slack_token": re.compile(r"xox[bpsa]-[a-zA-Z0-9\-]{20,}"),
    "stripe": re.compile(r"(sk|pk)_(test|live)_[a-zA-Z0-9]{20,}"),
    "huggingface": re.compile(r"hf_[a-zA-Z0-9]{20,}"),
    "generic_bearer": re.compile(r"Bearer\s+[a-zA-Z0-9\-_.]{20,}"),
    "generic_api_key": re.compile(
        r"(?:api[_-]?key|apikey|token|secret|password)"
        r"\s*[:=]\s*['\"]?([a-zA-Z0-9\-_.]{16,})['\"]?",
        re.IGNORECASE,
    ),
}


@dataclass
class VaultEntry:
    """รายการใน vault หนึ่งชิ้น."""

    vault_id: str
    provider: str
    key_hash: str  # SHA-256 ของ key — ใช้ verify โดยไม่ต้องเปิด key
    encrypted_key: str  # base64 ของ encrypted key
    created_at: str = ""
    last_used: str = ""
    use_count: int = 0
    tags: tuple[str, ...] = ()


class BlindVault:
    """ระบบเก็บ API Key แบบตาบอด.

    วิธีใช้ vault:
        vault = BlindVault()
        vid = vault.store("postman", "PMAK-xxxxx")
        # เก็บ key ใน vault โดยไม่มีใครเห็นค่าจริงอีก

        key = vault.retrieve(vid)
        # ดึง key ออกมาใช้งานตอน making API calls
    """

    def __init__(self, vault_dir: str | None = None):
        if vault_dir is None:
            vault_dir = os.path.expanduser("~/.ck-nexus/vault")
        self._vault_dir = Path(vault_dir)
        self._vault_dir.mkdir(parents=True, exist_ok=True)
        self._entries_file = self._vault_dir / "entries.jsonl"
        self._master_key = self._load_or_create_master_key()
        self._entries: dict[str, VaultEntry] = {}
        self._load_entries()

    def _load_or_create_master_key(self) -> bytes:
        """สร้างหรือโหลด master key สำหรับเข้ารหัส."""
        key_file = self._vault_dir / ".master_key"
        if key_file.exists():
            return base64.b64decode(key_file.read_text().strip())
        key = secrets.token_bytes(32)
        key_file.write_text(base64.b64encode(key).decode())
        key_file.chmod(0o600)
        return key

    def _encrypt(self, plaintext: str) -> str:
        """เข้ารหัส key ด้วย XOR + base64 ( lightweight — ไม่ใช้ external lib)."""
        key_bytes = self._master_key
        data = plaintext.encode()
        encrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(data)
        )
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, ciphertext: str) -> str:
        """ถอดรหัส key."""
        key_bytes = self._master_key
        data = base64.b64decode(ciphertext)
        decrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(data)
        )
        return decrypted.decode()

    def _hash_key(self, key: str) -> str:
        """สร้าง SHA-256 hash ของ key สำหรับ verify."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _generate_vault_id(self, provider: str) -> str:
        """สร้าง vault_id ไม่ซ้ำ."""
        rand = secrets.token_hex(4)
        return f"v-{provider}-{rand}"

    def _load_entries(self) -> None:
        """โหลด entries จากไฟล์."""
        if not self._entries_file.exists():
            return
        for line in self._entries_file.read_text().splitlines():
            if not line.strip():
                continue
            data = json.loads(line)
            entry = VaultEntry(**data)
            self._entries[entry.vault_id] = entry

    def _save_entry(self, entry: VaultEntry) -> None:
        """บันทึกลงไฟล์."""
        with open(self._entries_file, "a") as f:
            f.write(json.dumps({
                "vault_id": entry.vault_id,
                "provider": entry.provider,
                "key_hash": entry.key_hash,
                "encrypted_key": entry.encrypted_key,
                "created_at": entry.created_at,
                "last_used": entry.last_used,
                "use_count": entry.use_count,
                "tags": entry.tags,
            }) + "\n")

    # ─── Core API ───────────────────────────────────────

    def store(self, provider: str, key: str, *, tags: tuple[str, ...] = ()) -> str:
        """เก็บ key ใน vault — return vault_id.

        Agent เห็นแค่ vault_id ไม่เห็น key จริง
        """
        vid = self._generate_vault_id(provider)
        entry = VaultEntry(
            vault_id=vid,
            provider=provider,
            key_hash=self._hash_key(key),
            encrypted_key=self._encrypt(key),
            created_at=self._timestamp(),
            tags=tags,
        )
        self._entries[vid] = entry
        self._save_entry(entry)
        return vid

    def retrieve(self, vault_id: str) -> str:
        """ดึง key ออกมาใช้งาน."""
        entry = self._entries.get(vault_id)
        if not entry:
            raise KeyError(f"Vault entry not found: {vault_id}")
        entry.use_count += 1
        entry.last_used = self._timestamp()
        return self._decrypt(entry.encrypted_key)

    def verify(self, vault_id: str, key: str) -> bool:
        """ตรวจสอบว่า key ตรงกับที่เก็บไว้."""
        entry = self._entries.get(vault_id)
        if not entry:
            return False
        return entry.key_hash == self._hash_key(key)

    def list_entries(self, *, provider: str | None = None) -> list[dict]:
        """ดึงรายการ key ที่เก็บไว้ (ไม่เปิด key จริง)."""
        results = []
        for entry in self._entries.values():
            if provider and entry.provider != provider:
                continue
            results.append({
                "vault_id": entry.vault_id,
                "provider": entry.provider,
                "key_hash": entry.key_hash,
                "created_at": entry.created_at,
                "last_used": entry.last_used,
                "use_count": entry.use_count,
                "tags": entry.tags,
            })
        return results

    def delete(self, vault_id: str) -> bool:
        """ลบ key ออกจาก vault."""
        if vault_id in self._entries:
            del self._entries[vault_id]
            self._rewrite_entries()
            return True
        return False

    def _rewrite_entries(self) -> None:
        """เขียนไฟล์ใหม่ทั้งหมด."""
        with open(self._entries_file, "w") as f:
            for entry in self._entries.values():
                f.write(json.dumps({
                    "vault_id": entry.vault_id,
                    "provider": entry.provider,
                    "key_hash": entry.key_hash,
                    "encrypted_key": entry.encrypted_key,
                    "created_at": entry.created_at,
                    "last_used": entry.last_used,
                    "use_count": entry.use_count,
                    "tags": entry.tags,
                }) + "\n")

    def status(self) -> dict:
        """สถานะ vault."""
        providers: dict[str, int] = {}
        for entry in self._entries.values():
            providers[entry.provider] = providers.get(entry.provider, 0) + 1
        return {
            "total_keys": len(self._entries),
            "providers": providers,
            "vault_dir": str(self._vault_dir),
        }

    @staticmethod
    def _timestamp() -> str:
        import datetime
        return datetime.datetime.now(datetime.UTC).isoformat()


# ─── Blind Ingestion — จับ key จาก input แล้วเก็บอัตโนมัติ ─────

def scan_and_store(input_text: str, vault: BlindVault | None = None) -> list[dict]:
    """สแกนข้อความหา API key → เข้ารหัส → เก็บใน vault.

    Return list ของ {provider, vault_id, preview} — ไม่คืน key จริง
    """
    if vault is None:
        vault = BlindVault()

    found: list[dict] = []
    for provider, pattern in KEY_PATTERNS.items():
        for match in pattern.finditer(input_text):
            key_value = match.group(0)
            # ตรวจสอบว่า key นี้มีอยู่แล้วหรือยัง
            existing = [
                e for e in vault.list_entries(provider=provider)
                if vault.verify(e["vault_id"], key_value)
            ]
            if existing:
                found.append({
                    "provider": provider,
                    "vault_id": existing[0]["vault_id"],
                    "status": "already_stored",
                })
            else:
                vid = vault.store(provider, key_value)
                found.append({
                    "provider": provider,
                    "vault_id": vid,
                    "status": "stored",
                })
    return found
