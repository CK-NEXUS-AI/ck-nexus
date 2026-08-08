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
    environment: str = "development"
    openai_model: str = "gpt-5-mini"
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
    slack_bot_token: str = ""
    slack_api_base: str = "https://slack.com/api"
    google_drive_access_token: str = ""
    google_drive_api_base: str = "https://www.googleapis.com/drive/v3"
    n8n_base_url: str = ""
    n8n_api_key: str = ""
    integration_timeout_seconds: int = 5
    dev_team_enabled: bool = True
    dev_team_web_search_enabled: bool = True
    dev_team_max_turns: int = 8
    dev_architect_model: str = ""
    dev_research_model: str = ""
    dev_designer_model: str = ""
    dev_builder_model: str = ""
    dev_reviewer_model: str = ""

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

        configured = cls(
            environment=(
                os.getenv("CKNEXUS_ENVIRONMENT", "development").strip().lower()
                or "development"
            ),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
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
            slack_bot_token=os.getenv("SLACK_BOT_TOKEN", "").strip(),
            slack_api_base=os.getenv("SLACK_API_BASE", "https://slack.com/api").strip() or "https://slack.com/api",
            google_drive_access_token=os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", "").strip(),
            google_drive_api_base=os.getenv("GOOGLE_DRIVE_API_BASE", "https://www.googleapis.com/drive/v3").strip() or "https://www.googleapis.com/drive/v3",
            n8n_base_url=os.getenv("N8N_BASE_URL", "").strip(),
            n8n_api_key=os.getenv("N8N_API_KEY", "").strip(),
            integration_timeout_seconds=_as_int(
                os.getenv("CKNEXUS_INTEGRATION_TIMEOUT_SECONDS"),
                default=5,
                minimum=1,
                maximum=30,
            ),
            dev_team_enabled=_as_bool(os.getenv("CKNEXUS_DEV_TEAM_ENABLED"), default=True),
            dev_team_web_search_enabled=_as_bool(
                os.getenv("CKNEXUS_DEV_TEAM_WEB_SEARCH"), default=True
            ),
            dev_team_max_turns=_as_int(
                os.getenv("CKNEXUS_DEV_TEAM_MAX_TURNS"),
                default=8,
                minimum=2,
                maximum=20,
            ),
            dev_architect_model=os.getenv("CKNEXUS_MODEL_ARCHITECT", "").strip(),
            dev_research_model=os.getenv("CKNEXUS_MODEL_RESEARCH", "").strip(),
            dev_designer_model=os.getenv("CKNEXUS_MODEL_DESIGNER", "").strip(),
            dev_builder_model=os.getenv("CKNEXUS_MODEL_BUILDER", "").strip(),
            dev_reviewer_model=os.getenv("CKNEXUS_MODEL_REVIEWER", "").strip(),
        )
        configured.validate_startup()
        return configured

    def validate_startup(self) -> None:
        """Fail closed for production-only authentication invariants.

        Development and staging remain usable for local evidence collection. Production
        must never silently expose protected routes because a secret was omitted.
        """
        if self.environment != "production":
            return

        missing: list[str] = []
        if not _is_runtime_secret(self.access_token):
            missing.append("CKNEXUS_ACCESS_TOKEN")
        if self.email_gateway_enabled and not _is_runtime_secret(self.email_webhook_token):
            missing.append("CKNEXUS_EMAIL_WEBHOOK_TOKEN")
        if missing:
            names = ", ".join(missing)
            raise RuntimeError(f"Production startup blocked: configure secure values for {names}.")

    @property
    def openai_key_configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY", "").strip())


def _is_runtime_secret(value: str) -> bool:
    candidate = value.strip()
    if not candidate:
        return False
    return not candidate.upper().startswith("CHANGE_ME")
