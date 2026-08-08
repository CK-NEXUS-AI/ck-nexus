from __future__ import annotations

from dataclasses import dataclass

from opentelemetry import trace

from services.billing.plans import PlanTier, get_plan
from services.billing.stripe_client import StripeClient

tracer = trace.get_tracer(__name__)


@dataclass(slots=True)
class CheckoutResult:
    session_id: str
    checkout_url: str
    tenant_id: str
    plan_tier: PlanTier


class CheckoutService:
    def __init__(
        self,
        stripe_client: StripeClient,
        base_url: str,
    ) -> None:
        self.stripe = stripe_client
        self.base_url = base_url

    async def create_checkout(
        self,
        tenant_id: str,
        customer_email: str,
        plan_tier: PlanTier,
    ) -> CheckoutResult:
        with tracer.start_as_current_span("checkout.create") as span:
            span.set_attribute("tenant.id", tenant_id)
            span.set_attribute("plan.tier", plan_tier)

            plan = get_plan(plan_tier)

            session = await self.stripe.create_checkout_session(
                tenant_id=tenant_id,
                customer_email=customer_email,
                price_id=plan.stripe_price_id_monthly,
                success_url=f"{self.base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.base_url}/billing/cancel",
            )

            span.set_attribute("stripe.session_id", session.id)

            return CheckoutResult(
                session_id=session.id,
                checkout_url=session.url,
                tenant_id=tenant_id,
                plan_tier=plan_tier,
            )
