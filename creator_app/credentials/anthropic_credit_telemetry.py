from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from creator_app.credentials.credit_telemetry import CreditSnapshot


class AnthropicCostBudgetAdapter:
    """Anthropic monthly cost telemetry with a Priority-tier completeness guard.

    Anthropic's Claude Platform Admin Cost API reports service costs, but the
    provider documents that Priority Tier costs are excluded. This adapter
    therefore checks the Usage API for Priority-tier activity before allowing a
    percentage to become KNOWN. If Priority usage is present, observed cost is
    retained for diagnostics but the Credit Guard receives no percentage.
    """

    provider = "anthropic"
    cost_endpoint = "https://api.anthropic.com/v1/organizations/cost_report"
    usage_endpoint = "https://api.anthropic.com/v1/organizations/usage_report/messages"
    api_version = "2023-06-01"
    max_pages = 16

    def __init__(self, *, timeout: float = 8.0) -> None:
        self.timeout = timeout

    def collect(self) -> CreditSnapshot:
        key = os.getenv("ANTHROPIC_ADMIN_KEY", "").strip()
        budget_raw = os.getenv("CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD", "").strip()
        if not key or not budget_raw:
            return CreditSnapshot(
                provider=self.provider,
                state="UNKNOWN",
                source="anthropic.organization.cost_report",
                basis="configured_budget",
                detail=(
                    "ANTHROPIC_ADMIN_KEY or "
                    "CKNEXUS_ANTHROPIC_MONTHLY_BUDGET_USD missing"
                ),
            )

        try:
            budget = Decimal(budget_raw)
        except InvalidOperation:
            return self._error("invalid_budget")
        if not budget.is_finite() or budget <= 0:
            return self._error("budget_must_be_positive")

        now = datetime.now(UTC)
        start = datetime(now.year, now.month, 1, tzinfo=UTC)
        start_value = self._rfc3339(start)
        end_value = self._rfc3339(now)

        try:
            spent = self._collect_cost_usd(
                key=key,
                starting_at=start_value,
                ending_at=end_value,
            )
            priority_usage = self._has_priority_usage(
                key=key,
                starting_at=start_value,
                ending_at=end_value,
            )
        except urllib.error.HTTPError as exc:
            return self._error(f"http_{exc.code}")
        except (OSError, TimeoutError, ValueError, TypeError, InvalidOperation) as exc:
            return self._error(type(exc).__name__)

        spent_value = float(spent)
        budget_value = float(budget)
        if priority_usage:
            return CreditSnapshot(
                provider=self.provider,
                state="UNKNOWN",
                source="anthropic.organization.cost_report",
                used_amount=spent_value,
                total_amount=budget_value,
                currency="usd",
                basis="configured_budget",
                detail="priority_tier_usage_not_in_cost_report; percentage not guessed",
            )

        remaining = max(Decimal("0"), budget - spent)
        remaining_pct = min(Decimal("100"), (remaining / budget) * Decimal("100"))
        return CreditSnapshot(
            provider=self.provider,
            state="KNOWN",
            source="anthropic.organization.cost_report",
            remaining_pct=float(remaining_pct),
            remaining_amount=float(remaining),
            used_amount=spent_value,
            total_amount=budget_value,
            currency="usd",
            basis="configured_budget",
            detail="cost telemetry may reflect provider reporting delay",
        )

    def _collect_cost_usd(
        self,
        *,
        key: str,
        starting_at: str,
        ending_at: str,
    ) -> Decimal:
        params: dict[str, object] = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "bucket_width": "1d",
            "limit": 31,
        }
        spent_cents = Decimal("0")

        for _ in range(self.max_pages):
            payload = self._request_json(self.cost_endpoint, params, key)
            buckets = payload.get("data")
            if not isinstance(buckets, list):
                raise ValueError("invalid_cost_schema")

            for bucket in buckets:
                if not isinstance(bucket, dict):
                    continue
                results = bucket.get("results", [])
                if not isinstance(results, list):
                    raise ValueError("invalid_cost_results")
                for result in results:
                    if not isinstance(result, dict):
                        continue
                    if str(result.get("currency", "USD")).upper() != "USD":
                        continue
                    spent_cents += Decimal(str(result.get("amount", "0")))

            if not payload.get("has_more", False):
                return spent_cents / Decimal("100")
            next_page = payload.get("next_page")
            if not isinstance(next_page, str) or not next_page:
                raise ValueError("missing_cost_page_cursor")
            params["page"] = next_page

        raise ValueError("cost_pagination_limit_exceeded")

    def _has_priority_usage(
        self,
        *,
        key: str,
        starting_at: str,
        ending_at: str,
    ) -> bool:
        params: dict[str, object] = {
            "starting_at": starting_at,
            "ending_at": ending_at,
            "bucket_width": "1d",
            "limit": 31,
            "service_tiers[]": ["priority", "priority_on_demand"],
        }

        for _ in range(self.max_pages):
            payload = self._request_json(self.usage_endpoint, params, key)
            buckets = payload.get("data")
            if not isinstance(buckets, list):
                raise ValueError("invalid_usage_schema")

            for bucket in buckets:
                if not isinstance(bucket, dict):
                    continue
                results = bucket.get("results", [])
                if not isinstance(results, list):
                    raise ValueError("invalid_usage_results")
                for result in results:
                    if isinstance(result, dict) and self._result_has_positive_usage(result):
                        return True

            if not payload.get("has_more", False):
                return False
            next_page = payload.get("next_page")
            if not isinstance(next_page, str) or not next_page:
                raise ValueError("missing_usage_page_cursor")
            params["page"] = next_page

        raise ValueError("usage_pagination_limit_exceeded")

    def _request_json(
        self,
        endpoint: str,
        params: dict[str, object],
        key: str,
    ) -> dict[str, object]:
        query = urllib.parse.urlencode(params, doseq=True)
        request = urllib.request.Request(
            f"{endpoint}?{query}",
            headers={
                "anthropic-version": self.api_version,
                "User-Agent": "CK-NEXUS/0.2",
                "x-api-key": key,
            },
        )
        # B310 is safe: callers pass only class-owned fixed HTTPS endpoints.
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("invalid_anthropic_response")
        return payload

    @staticmethod
    def _result_has_positive_usage(result: dict[str, object]) -> bool:
        scalar_fields = (
            "uncached_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        )
        for field in scalar_fields:
            value = result.get(field, 0)
            if isinstance(value, int | float) and value > 0:
                return True

        cache_creation = result.get("cache_creation")
        if isinstance(cache_creation, dict):
            for value in cache_creation.values():
                if isinstance(value, int | float) and value > 0:
                    return True

        server_tool_use = result.get("server_tool_use")
        if isinstance(server_tool_use, dict):
            for value in server_tool_use.values():
                if isinstance(value, int | float) and value > 0:
                    return True
        return False

    def _error(self, detail: str) -> CreditSnapshot:
        return CreditSnapshot(
            provider=self.provider,
            state="ERROR",
            source="anthropic.organization.cost_report",
            basis="configured_budget",
            detail=detail,
        )

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        return value.isoformat().replace("+00:00", "Z")
