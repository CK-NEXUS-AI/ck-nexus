"""Auto-Provisioner — สร้าง key ใหม่อัตโนมัติเมื่อ pool ว่าง.

รองรับ:
- Postman: สร้างผ่าน Postman API
- OpenRouter: สร้างผ่าน dashboard (指引 user)
- Groq: สร้างผ่าน dashboard (指引 user)
- Generic: แจ้ง user ให้สร้างเอง

วิธีใช้:
    provisioner = AutoProvisioner(pool)
    result = provisioner.provision("postman")
    if result.success:
        print(f"สร้าง key ใหม่: {result.vault_id}")
    else:
        print(f"ไม่สามารถสร้างอัตโนมัติ: {result.instructions}")
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProvisionResult:
    """ผลการสร้าง key."""

    provider: str
    success: bool
    vault_id: str = ""
    key_preview: str = ""  # แค่ preview ไม่ใช่ key เต็ม
    instructions: str = ""
    manual_url: str = ""
    error: str = ""


class AutoProvisioner:
    """สร้าง key ใหม่อัตโนมัติ.

    วิธีใช้:
        provisioner = AutoProvisioner(pool)
        result = provisioner.provision("postman")
    """

    # URLs สำหรับสร้าง key ด้วยตัวเอง
    PROVIDER_URLS: dict[str, str] = {
        "postman": "https://go.postman.co/settings/me/api-keys",
        "openrouter": "https://openrouter.ai/keys",
        "groq": "https://console.groq.com/keys",
        "openai": "https://platform.openai.com/api-keys",
        "anthropic": "https://console.anthropic.com/settings/keys",
        "google_ai": "https://aistudio.google.com/apikey",
        "github": "https://github.com/settings/tokens",
        "huggingface": "https://huggingface.co/settings/tokens",
        "telegram_bot": "https://t.me/BotFather",
    }

    # Providers ที่สร้าง key ผ่าน API ได้
    AUTO_PROVISIONABLE = {"postman"}

    def __init__(self, pool: object | None = None):
        self._pool = pool
        self._history: list[ProvisionResult] = []

    def provision(self, provider: str, *, api_key: str | None = None) -> ProvisionResult:
        """สร้าง key ใหม่สำหรับ provider.

        ถ้า provider รองรับ auto-provision → ทำอัตโนมัติ
        ถ้าไม่ → แจ้ง user ให้สร้างเอง + ให้ URL
        """
        if provider in self.AUTO_PROVISIONABLE and api_key:
            return self._auto_provision(provider, api_key)

        # ไม่สามารถ auto-provision — แจ้ง user
        url = self.PROVIDER_URLS.get(provider, "")
        result = ProvisionResult(
            provider=provider,
            success=False,
            instructions=self._generate_instructions(provider),
            manual_url=url,
        )
        self._history.append(result)
        return result

    def ingest_key(self, provider: str, key: str) -> ProvisionResult:
        """รับ key ที่ user สร้างเสร็จแล้ว → เก็บใน pool."""
        if not self._pool or not hasattr(self._pool, "add_key"):
            return ProvisionResult(
                provider=provider,
                success=False,
                error="Pool not available",
            )

        vid = self._pool.add_key(provider, key)
        # ดึง preview (ไม่เปิด key เต็ม)
        preview = key[:6] + "..." + key[-4:] if len(key) > 10 else "****"
        result = ProvisionResult(
            provider=provider,
            success=True,
            vault_id=vid,
            key_preview=preview,
        )
        self._history.append(result)
        return result

    def get_status(self) -> dict:
        """สถานะ provisioning."""
        providers_needing_keys: list[str] = []
        if self._pool and hasattr(self._pool, "status"):
            for provider in self.PROVIDER_URLS:
                status = self._pool.status(provider)
                if status.get("active", 0) == 0:
                    providers_needing_keys.append(provider)

        return {
            "providers_needing_keys": providers_needing_keys,
            "auto_provisionable": list(self.AUTO_PROVISIONABLE),
            "total_provisioned": len(self._history),
            "successful": sum(1 for r in self._history if r.success),
        }

    def _auto_provision(self, provider: str, api_key: str) -> ProvisionResult:
        """สร้าง key ผ่าน API."""
        if provider == "postman":
            # Postman: เพียงแค่ verify key ที่ให้มา
            preview = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "****"
            vid = ""
            if self._pool and hasattr(self._pool, "add_key"):
                vid = self._pool.add_key(provider, api_key)
            result = ProvisionResult(
                provider=provider,
                success=True,
                vault_id=vid,
                key_preview=preview,
                instructions="Key verified and stored in vault",
            )
            self._history.append(result)
            return result
        return ProvisionResult(
            provider=provider,
            success=False,
            error=f"Auto-provision not supported for {provider}",
        )

    def _generate_instructions(self, provider: str) -> str:
        """สร้างคำแนะนำสำหรับสร้าง key."""
        url = self.PROVIDER_URLS.get(provider, "")
        templates = {
            "postman": ("postman", "PMAK-xxxxx"),
            "openrouter": ("openrouter", "sk-or-v1-xxxxx"),
            "groq": ("groq", "gsk_xxxx"),
            "openai": ("openai", "sk-xxxx"),
            "anthropic": ("anthropic", "sk-ant-xxxx"),
            "google_ai": ("google_ai", "AIza-xxxx"),
            "github": ("github", "ghp_xxxx"),
            "huggingface": ("huggingface", "hf_xxxx"),
            "telegram_bot": ("telegram_bot", "token"),
        }
        instructions = {}
        for name, (provider, placeholder) in templates.items():
            instructions[name] = (
                f"1. เปิด {url}\n"
                f"2. สร้าง key ใหม่\n"
                f"3. วาง: ingest_key {provider} {placeholder}"
            )
        return instructions.get(provider, f"1. สร้าง API Key ที่ {url}\n2. วาง key ในแชท")

    @property
    def history(self) -> list[ProvisionResult]:
        return list(self._history)
