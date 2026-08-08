from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

RUNTIME_ROOT = Path.cwd()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(
    value: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    return max(minimum, min(parsed, maximum))


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "CK-NEXUS Creator Edition"
    app_version: str = "0.2.0"
    openai_model: str = "gpt-5.6-luna"
    database_url: str = ""
    session_database_url: str = ""
    database_path: Path = RUNTIME_ROOT / "data" / "cknexus.db"
    mock_ai: bool = False
    access_token: str = ""
    max_prompt_chars: int = 8_000
    history_limit: int = 30
    rate_limit_per_minute: int = 10
    run_timeout_seconds: int = 90
    max_request_bytes: int = 65_536
    codex_enabled: bool = False
    codex_bin: str = "codex"
    codex_home: Path | None = None
    codex_workspace: Path = RUNTIME_ROOT
    codex_sandbox: str = "read-only"
    codex_timeout_seconds: int = 600
    codex_max_output_chars: int = 100_000
    email_gateway_enabled: bool = False
    email_database_url: str = ""
    email_database_path: Path | None = None
    email_webhook_token: str = ""
    email_lease_seconds: int = 300
    github_token: str = ""
    github_repo: str = ""
    github_api_base: str = "https://api.github.com"

    @classmethod
    def from_env(cls) -> Settings:
        configured_root = os.getenv("CKNEXUS_HOME", "").strip()
        runtime_root = Path(configured_root).expanduser() if configured_root else Path.cwd()
        runtime_root = runtime_root.resolve()
        load_dotenv(runtime_root / ".env.local", override=False)
        database_value = os.getenv("CKNEXUS_DATABASE_PATH", "data/cknexus.db")
        database_path = Path(database_value)
        if not database_path.is_absolute():
            database_path = runtime_root / database_path

        email_database_value = os.getenv("CKNEXUS_EMAIL_DATABASE_PATH", "").strip()
        if email_database_value:
            email_database_path = Path(email_database_value).expanduser()
            if not email_database_path.is_absolute():
                email_database_path = runtime_root / email_database_path
        else:
            email_database_path = database_path

        codex_workspace_value = os.getenv("CKNEXUS_CODEX_WORKSPACE", "").strip()
        codex_workspace = (
            Path(codex_workspace_value).expanduser()
            if codex_workspace_value
            else runtime_root
        ).resolve()
        codex_home_value = os.getenv("CKNEXUS_CODEX_HOME", "").strip()
        codex_home = Path(codex_home_value).expanduser().resolve() if codex_home_value else None
        codex_sandbox = os.getenv("CKNEXUS_CODEX_SANDBOX", "read-only").strip()
        if codex_sandbox not in {"read-only", "workspace-write"}:
            codex_sandbox = "read-only"

        database_url = os.getenv("CKNEXUS_DATABASE_URL", "").strip()
        session_database_url = os.getenv("CKNEXUS_SESSION_DATABASE_URL", "").strip()
        if not session_database_url and database_url.startswith("postgresql://"):
            session_database_url = "postgresql+asyncpg://" + database_url.removeprefix("postgresql://")
        elif not session_database_url and database_url.startswith("postgres://"):
            session_database_url = "postgresql+asyncpg://" + database_url.removeprefix("postgres://")

        return cls(
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
            database_url=database_url,
            session_database_url=session_database_url,
            database_path=database_path,
            mock_ai=_as_bool(os.getenv("CKNEXUS_MOCK_AI"), default=False),
            access_token=os.getenv("CKNEXUS_ACCESS_TOKEN", ""),
            max_prompt_chars=_as_int(
                os.getenv("CKNEXUS_MAX_PROMPT_CHARS"),
                default=8_000,
                minimum=500,
                maximum=50_000,
            ),
            history_limit=_as_int(
                os.getenv("CKNEXUS_HISTORY_LIMIT"),
                default=30,
                minimum=1,
                maximum=100,
            ),
            rate_limit_per_minute=_as_int(
                os.getenv("CKNEXUS_RATE_LIMIT_PER_MINUTE"),
                default=10,
                minimum=1,
                maximum=1_000,
            ),
            run_timeout_seconds=_as_int(
                os.getenv("CKNEXUS_RUN_TIMEOUT_SECONDS"),
                default=90,
                minimum=10,
                maximum=600,
            ),
            max_request_bytes=_as_int(
                os.getenv("CKNEXUS_MAX_REQUEST_BYTES"),
                default=65_536,
                minimum=8_192,
                maximum=1_048_576,
            ),
            codex_enabled=_as_bool(os.getenv("CKNEXUS_CODEX_ENABLED"), default=False),
            codex_bin=os.getenv("CKNEXUS_CODEX_BIN", "codex").strip() or "codex",
            codex_home=codex_home,
            codex_workspace=codex_workspace,
            codex_sandbox=codex_sandbox,
            codex_timeout_seconds=_as_int(
                os.getenv("CKNEXUS_CODEX_TIMEOUT_SECONDS"),
                default=600,
                minimum=30,
                maximum=3_600,
            ),
            codex_max_output_chars=_as_int(
                os.getenv("CKNEXUS_CODEX_MAX_OUTPUT_CHARS"),
                default=100_000,
                minimum=1_000,
                maximum=500_000,
            ),
            email_database_url=os.getenv("CKNEXUS_EMAIL_DATABASE_URL", "").strip(),
            email_gateway_enabled=_as_bool(
                os.getenv("CKNEXUS_EMAIL_GATEWAY_ENABLED"), default=False
            ),
            email_database_path=email_database_path,
            email_webhook_token=os.getenv("CKNEXUS_EMAIL_WEBHOOK_TOKEN", ""),
            email_lease_seconds=_as_int(
                os.getenv("CKNEXUS_EMAIL_LEASE_SECONDS"),
                default=300,
                minimum=30,
                maximum=3_600,
            ),
            github_token=os.getenv("GITHUB_TOKEN", "").strip(),
            github_repo=os.getenv("GITHUB_REPO", "").strip(),
            github_api_base=os.getenv("GITHUB_API_BASE", "https://api.github.com").strip() or "https://api.github.com",
        )

    @property
    def openai_key_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY", "").strip())
