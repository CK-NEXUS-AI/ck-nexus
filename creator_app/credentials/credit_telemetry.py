from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from creator_app.credentials.free_fallback_keypool import FreeFallbackKeyPool


@dataclass(frozen=True, slots=True)
class CreditSnapshot:
    provider: str
    state: str
    source: str
    remaining_pct: float | None = None
    used_amount: float | None = None
    total_amount: float | None = None
    currency: str | None = None
    basis: str | None = None
    detail: str | None = None
    observed_at: str = ""

    def __post_init__(self) -> None:
        if not self.observed_at:
            object.__setattr__(self, "observed_at", datetime.now(UTC).isoformat())
        if self.remaining_pct is not None and not 0.0 <= self.remaining_pct <= 100.0:
            raise ValueError("remaining_pct must be between 0 and 100")


class CreditTelemetryAdapter(Protocol):
    provider: str

    def collect(self) -> CreditSnapshot: ...


class OpenRouterCreditsAdapter:
    """Authoritative OpenRouter credit balance using the management-key endpoint."""

    provider = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/credits"

    def __init__(self, *, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def collect(self) -> CreditSnapshot:
        key = os.getenv("OPENROUTER_MANAGEMENT_KEY", "").strip()
        if not key:
            return CreditSnapshot(
                provider=self.provider,
                state="UNKNOWN",
                source="openrouter.credits",
                detail="OPENROUTER_MANAGEMENT_KEY is not configured",
            )

        request = urllib.request.Request(
            self.endpoint,
            headers={"Authorization": f"Bearer {key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openrouter.credits",
                detail=f"http_{exc.code}",
            )
        except Exception as exc:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openrouter.credits",
                detail=type(exc).__name__,
            )

        data = payload.get("data", {})
        try:
            total = float(data["total_credits"])
            used = float(data["total_usage"])
        except (KeyError, TypeError, ValueError):
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openrouter.credits",
                detail="invalid_response_schema",
            )

        if total <= 0:
            return CreditSnapshot(
                provider=self.provider,
                state="UNKNOWN",
                source="openrouter.credits",
                used_amount=used,
                total_amount=total,
                currency="usd",
                basis="provider_credit",
                detail="total_credits_not_positive",
            )

        remaining = max(0.0, total - used)
        remaining_pct = min(100.0, (remaining / total) * 100.0)
        return CreditSnapshot(
            provider=self.provider,
            state="KNOWN",
            source="openrouter.credits",
            remaining_pct=remaining_pct,
            used_amount=used,
            total_amount=total,
            currency="usd",
            basis="provider_credit",
        )


class OpenAICostBudgetAdapter:
    """OpenAI organization costs normalized against an explicit monthly budget."""

    provider = "openai"
    endpoint = "https://api.openai.com/v1/organization/costs"

    def __init__(self, *, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def collect(self) -> CreditSnapshot:
        admin_key = os.getenv("OPENAI_ADMIN_KEY", "").strip()
        budget_raw = os.getenv("CKNEXUS_OPENAI_MONTHLY_BUDGET_USD", "").strip()
        if not admin_key or not budget_raw:
            return CreditSnapshot(
                provider=self.provider,
                state="UNKNOWN",
                source="openai.organization.costs",
                basis="configured_budget",
                detail="OPENAI_ADMIN_KEY or CKNEXUS_OPENAI_MONTHLY_BUDGET_USD missing",
            )

        try:
            budget = float(budget_raw)
        except ValueError:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openai.organization.costs",
                basis="configured_budget",
                detail="invalid_budget",
            )
        if budget <= 0:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openai.organization.costs",
                basis="configured_budget",
                detail="budget_must_be_positive",
            )

        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        params = urllib.parse.urlencode(
            {
                "start_time": int(start.timestamp()),
                "end_time": int(now.timestamp()) + 1,
                "bucket_width": "1d",
                "limit": 31,
            }
        )
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={"Authorization": f"Bearer {admin_key}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openai.organization.costs",
                basis="configured_budget",
                detail=f"http_{exc.code}",
            )
        except Exception as exc:
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openai.organization.costs",
                basis="configured_budget",
                detail=type(exc).__name__,
            )

        spent = 0.0
        try:
            for bucket in payload.get("data", []):
                for result in bucket.get("results", []):
                    amount = result.get("amount", {})
                    if str(amount.get("currency", "usd")).lower() != "usd":
                        continue
                    spent += float(amount.get("value", 0.0))
        except (TypeError, ValueError):
            return CreditSnapshot(
                provider=self.provider,
                state="ERROR",
                source="openai.organization.costs",
                basis="configured_budget",
                detail="invalid_response_schema",
            )

        remaining = max(0.0, budget - spent)
        remaining_pct = min(100.0, (remaining / budget) * 100.0)
        return CreditSnapshot(
            provider=self.provider,
            state="KNOWN",
            source="openai.organization.costs",
            remaining_pct=remaining_pct,
            used_amount=spent,
            total_amount=budget,
            currency="usd",
            basis="configured_budget",
        )


class CreditTelemetryFabric:
    """Collect trusted credit telemetry and feed only known values to Credit Guard."""

    DEFAULT_EVIDENCE_PATH = "data/credit-telemetry.jsonl"

    def __init__(
        self,
        pool: FreeFallbackKeyPool,
        *,
        adapters: list[CreditTelemetryAdapter] | None = None,
        evidence_path: str | None = None,
    ) -> None:
        self.pool = pool
        self.adapters = adapters or [OpenRouterCreditsAdapter(), OpenAICostBudgetAdapter()]
        self.evidence_path = evidence_path or os.getenv(
            "CKNEXUS_CREDIT_TELEMETRY_EVIDENCE_PATH",
            self.DEFAULT_EVIDENCE_PATH,
        )
        self.latest: dict[str, CreditSnapshot] = {}

    def collect_once(self) -> dict[str, CreditSnapshot]:
        """Collect one cycle. UNKNOWN/ERROR telemetry never activates the credit guard."""
        configured = {spec.id for spec in self.pool.specs}
        collected: dict[str, CreditSnapshot] = {}

        for adapter in self.adapters:
            if adapter.provider not in configured:
                continue
            snapshot = adapter.collect()
            collected[snapshot.provider] = snapshot
            self.latest[snapshot.provider] = snapshot
            self._append_evidence(snapshot)
            if snapshot.state == "KNOWN" and snapshot.remaining_pct is not None:
                self._apply_known_snapshot(snapshot)

        for provider in sorted(configured - set(collected)):
            snapshot = CreditSnapshot(
                provider=provider,
                state="UNKNOWN",
                source="unsupported_provider",
                detail="no authoritative credit adapter configured",
            )
            collected[provider] = snapshot
            self.latest[provider] = snapshot
            self._append_evidence(snapshot)

        return collected

    def status(self) -> dict[str, object]:
        return {
            "providers": {
                provider: asdict(snapshot)
                for provider, snapshot in sorted(self.latest.items())
            },
            "unknown_policy": "DO_NOT_GUESS",
            "evidence_path": self.evidence_path,
        }

    def _apply_known_snapshot(self, snapshot: CreditSnapshot) -> None:
        remaining = snapshot.remaining_pct
        if remaining is None or remaining > self.pool.remaining_threshold_pct:
            return
        self.pool.activate_free_only(
            reason=(
                f"credit telemetry {snapshot.provider} remaining {remaining:.2f}% "
                f"<= guard {self.pool.remaining_threshold_pct:.2f}% "
                f"source={snapshot.source}"
            )
        )

    def _append_evidence(self, snapshot: CreditSnapshot) -> None:
        if not self.evidence_path:
            return
        path = Path(os.path.expanduser(self.evidence_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "schema": "cknexus.credit-telemetry.v1",
            **asdict(snapshot),
            "credential_material_logged": False,
            "authority": "CK-NEXUS",
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
