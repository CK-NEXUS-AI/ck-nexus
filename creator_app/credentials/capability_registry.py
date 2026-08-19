from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Capability(StrEnum):
    OPENAI_RESPONSES = "openai.responses"
    GITHUB_REPO_READ = "github.repo.read"
    GITHUB_REPO_WRITE = "github.repo.write"
    SLACK_MESSAGES_READ = "slack.messages.read"
    SLACK_MESSAGES_WRITE = "slack.messages.write"
    GOOGLE_DRIVE_READ = "google.drive.read"
    GMAIL_READ = "gmail.read"
    HUBSPOT_CRM_READ = "hubspot.crm.read"
    AIRTABLE_RECORDS_READ = "airtable.records.read"
    POSTGRES_QUERY = "postgres.query"


@dataclass(frozen=True, slots=True)
class CapabilitySpec:
    capability: Capability
    label: str
    description: str
    required_consumer: str
    credential_ids: tuple[str, ...] = ()
    provider_scopes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderCandidate:
    provider: str
    capability: Capability
    credential_id: str
    scopes: tuple[str, ...] = ()
    account_tenant_id: str = ""
    expiry_seconds: int = 0
    health: str = "unknown"
    quota_remaining: int = -1
    quota_total: int = -1
    rate_limit_state: str = "normal"
    cost: float = 0.0
    latency_ms: int = 0
    region: str = ""
    policy_risk: str = "low"
    priority: int = 100

    def quota_percentage_used(self) -> float | None:
        if self.quota_remaining < 0 or self.quota_total <= 0:
            return None
        used = self.quota_total - self.quota_remaining
        return (used / self.quota_total) * 100

    def is_quota_exhausted(self, *, warning_threshold_pct: float = 95.0) -> bool:
        pct = self.quota_percentage_used()
        if pct is None:
            return False
        return pct >= warning_threshold_pct

    def as_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "capability": self.capability.value,
            "credential_id": self.credential_id,
            "scopes": list(self.scopes),
            "account_tenant_id": self.account_tenant_id,
            "expiry_seconds": self.expiry_seconds,
            "health": self.health,
            "quota_remaining": self.quota_remaining,
            "quota_total": self.quota_total,
            "rate_limit_state": self.rate_limit_state,
            "cost": self.cost,
            "latency_ms": self.latency_ms,
            "region": self.region,
            "policy_risk": self.policy_risk,
            "priority": self.priority,
        }


CANONICAL_CAPABILITIES: dict[str, CapabilitySpec] = {
    Capability.OPENAI_RESPONSES.value: CapabilitySpec(
        capability=Capability.OPENAI_RESPONSES,
        label="OpenAI Responses",
        description="Request chat completions from OpenAI-compatible providers.",
        required_consumer="provider.openai",
        credential_ids=("openai.api_key",),
    ),
    Capability.GITHUB_REPO_READ.value: CapabilitySpec(
        capability=Capability.GITHUB_REPO_READ,
        label="GitHub Repo Read",
        description="Read repository contents and metadata via GitHub App or token.",
        required_consumer="github.app",
        credential_ids=(
            "github.app_id",
            "github.app_private_key",
            "github.app_installation_id",
            "github.installation_token",
        ),
        provider_scopes=("repo", "read:org"),
    ),
    Capability.GITHUB_REPO_WRITE.value: CapabilitySpec(
        capability=Capability.GITHUB_REPO_WRITE,
        label="GitHub Repo Write",
        description="Write to repositories via GitHub App (push, PRs, tags).",
        required_consumer="github.app",
        credential_ids=(
            "github.app_id",
            "github.app_private_key",
            "github.app_installation_id",
            "github.installation_token",
        ),
        provider_scopes=("repo", "workflow"),
    ),
    Capability.SLACK_MESSAGES_READ.value: CapabilitySpec(
        capability=Capability.SLACK_MESSAGES_READ,
        label="Slack Messages Read",
        description="Search and read Slack messages.",
        required_consumer="slack.app",
        provider_scopes=("channels:history", "groups:history", "im:history"),
    ),
    Capability.SLACK_MESSAGES_WRITE.value: CapabilitySpec(
        capability=Capability.SLACK_MESSAGES_WRITE,
        label="Slack Messages Write",
        description="Post messages to Slack channels.",
        required_consumer="slack.app",
        provider_scopes=("chat:write", "chat:write.public"),
    ),
    Capability.GOOGLE_DRIVE_READ.value: CapabilitySpec(
        capability=Capability.GOOGLE_DRIVE_READ,
        label="Google Drive Read",
        description="Read files from Google Drive via connected app.",
        required_consumer="google.app",
        provider_scopes=("https://www.googleapis.com/auth/drive.readonly",),
    ),
    Capability.GMAIL_READ.value: CapabilitySpec(
        capability=Capability.GMAIL_READ,
        label="Gmail Read",
        description="Read/search Gmail via OAuth2 — never raw tokens.",
        required_consumer="gmail.oauth",
        credential_ids=(
            "gmail.client_id",
            "gmail.client_secret",
            "gmail.access_token",
            "gmail.refresh_token",
        ),
        provider_scopes=("https://www.googleapis.com/auth/gmail.readonly",),
    ),
    Capability.HUBSPOT_CRM_READ.value: CapabilitySpec(
        capability=Capability.HUBSPOT_CRM_READ,
        label="HubSpot CRM Read",
        description="Read CRM contacts and records from HubSpot.",
        required_consumer="hubspot.app",
        provider_scopes=("crm.objects.contacts.read",),
    ),
    Capability.AIRTABLE_RECORDS_READ.value: CapabilitySpec(
        capability=Capability.AIRTABLE_RECORDS_READ,
        label="Airtable Records Read",
        description="Read records from Airtable bases via connected app.",
        required_consumer="airtable.app",
        provider_scopes=("data.records:read",),
    ),
    Capability.POSTGRES_QUERY.value: CapabilitySpec(
        capability=Capability.POSTGRES_QUERY,
        label="Postgres Query",
        description="Execute parameterized SELECT queries against Postgres.",
        required_consumer="postgres.app",
        provider_scopes=(),
    ),
}


class CapabilityRegistry:
    """Registry of capabilities with their required credentials and scopes."""

    def __init__(
        self,
        capabilities: dict[str, CapabilitySpec] | None = None,
    ) -> None:
        self._capabilities = dict(capabilities or CANONICAL_CAPABILITIES)

    def list(self) -> tuple[str, ...]:
        return tuple(sorted(self._capabilities.keys()))

    def get(self, capability: str) -> CapabilitySpec | None:
        return self._capabilities.get(capability)

    def required_credentials(self, capability: str) -> tuple[str, ...]:
        spec = self._capabilities.get(capability)
        if spec is None:
            return ()
        return spec.credential_ids

    def required_scopes(self, capability: str) -> tuple[str, ...]:
        spec = self._capabilities.get(capability)
        if spec is None:
            return ()
        return spec.provider_scopes

    def consumer_for(self, capability: str) -> str | None:
        spec = self._capabilities.get(capability)
        if spec is None:
            return None
        return spec.required_consumer

    @classmethod
    def from_file(cls, path: Path) -> CapabilityRegistry:
        data = json.loads(path.read_text(encoding="utf-8"))
        caps: dict[str, CapabilitySpec] = {}
        for entry in data.get("capabilities", []):
            caps[entry["capability"]] = CapabilitySpec(
                capability=Capability(entry["capability"]),
                label=entry.get("label", entry["capability"]),
                description=entry.get("description", ""),
                required_consumer=entry["required_consumer"],
                credential_ids=tuple(entry.get("credential_ids", [])),
                provider_scopes=tuple(entry.get("provider_scopes", [])),
            )
        return cls(caps)
