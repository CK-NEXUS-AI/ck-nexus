from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class PlanTier(StrEnum):
    STARTER = "starter"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class BillingInterval(StrEnum):
    MONTHLY = "month"
    YEARLY = "year"


@dataclass(slots=True, frozen=True)
class Plan:
    tier: PlanTier
    name: str
    price_thb: int
    price_usd: int
    stripe_price_id_monthly: str
    stripe_price_id_yearly: str
    interval: BillingInterval
    max_agents: int
    max_workflows: int
    max_api_calls_per_month: int
    features: list[str] = field(default_factory=list)


PLANS: dict[PlanTier, Plan] = {
    PlanTier.STARTER: Plan(
        tier=PlanTier.STARTER,
        name="Starter",
        price_thb=990,
        price_usd=27,
        stripe_price_id_monthly="price_starter_monthly",
        stripe_price_id_yearly="price_starter_yearly",
        interval=BillingInterval.MONTHLY,
        max_agents=3,
        max_workflows=10,
        max_api_calls_per_month=10_000,
        features=[
            "AI Chatbot",
            "Knowledge Base",
            "Basic Analytics",
            "Email Support",
        ],
    ),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO,
        name="Pro",
        price_thb=4_900,
        price_usd=137,
        stripe_price_id_monthly="price_pro_monthly",
        stripe_price_id_yearly="price_pro_yearly",
        interval=BillingInterval.MONTHLY,
        max_agents=20,
        max_workflows=100,
        max_api_calls_per_month=100_000,
        features=[
            "Everything in Starter",
            "Multi-Agent Workflows",
            "Revenue Dashboard",
            "Temporal Workflows",
            "Priority Support",
        ],
    ),
    PlanTier.ENTERPRISE: Plan(
        tier=PlanTier.ENTERPRISE,
        name="Enterprise",
        price_thb=49_000,
        price_usd=1_370,
        stripe_price_id_monthly="price_enterprise_monthly",
        stripe_price_id_yearly="price_enterprise_yearly",
        interval=BillingInterval.MONTHLY,
        max_agents=-1,
        max_workflows=-1,
        max_api_calls_per_month=-1,
        features=[
            "Everything in Pro",
            "Unlimited Agents",
            "Custom AI Models",
            "SSO / SAML",
            "SLA 99.9%",
            "Dedicated Support",
            "Custom Contracts",
        ],
    ),
}


def get_plan(tier: PlanTier) -> Plan:
    return PLANS[tier]


def get_plan_by_stripe_price_id(price_id: str) -> Plan | None:
    for plan in PLANS.values():
        if price_id in (
            plan.stripe_price_id_monthly,
            plan.stripe_price_id_yearly,
        ):
            return plan
    return None


def is_within_limits(
    plan: Plan,
    resource: str,
    current_count: int,
) -> bool:
    limits: dict[str, int] = {
        "agents": plan.max_agents,
        "workflows": plan.max_workflows,
        "api_calls": plan.max_api_calls_per_month,
    }

    limit = limits.get(resource, 0)

    if limit == -1:
        return True

    return current_count < limit
