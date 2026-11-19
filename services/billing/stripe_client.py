from __future__ import annotations

import stripe
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class StripeClient:
    def __init__(self, api_key: str) -> None:
        stripe.api_key = api_key
        self._stripe = stripe

    async def create_checkout_session(
        self,
        tenant_id: str,
        customer_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> stripe.checkout.Session:
        with tracer.start_as_current_span("stripe.create_checkout_session") as span:
            span.set_attribute("tenant.id", tenant_id)
            span.set_attribute("stripe.price_id", price_id)

            session = self._stripe.checkout.Session.create(
                customer_email=customer_email,
                payment_method_types=["card"],
                line_items=[{"price": price_id, "quantity": 1}],
                mode="subscription",
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={"tenant_id": tenant_id},
                subscription_data={"metadata": {"tenant_id": tenant_id}},
            )

            span.set_attribute("stripe.session_id", session.id)
            return session

    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> stripe.billing_portal.Session:
        with tracer.start_as_current_span("stripe.create_portal_session"):
            return self._stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )

    async def retrieve_subscription(
        self,
        subscription_id: str,
    ) -> stripe.Subscription:
        with tracer.start_as_current_span("stripe.retrieve_subscription"):
            return self._stripe.Subscription.retrieve(subscription_id)

    async def cancel_subscription(
        self,
        subscription_id: str,
    ) -> stripe.Subscription:
        with tracer.start_as_current_span("stripe.cancel_subscription"):
            return self._stripe.Subscription.cancel(subscription_id)

    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
        webhook_secret: str,
    ) -> stripe.Event:
        return self._stripe.Webhook.construct_event(
            payload,
            sig_header,
            webhook_secret,
        )
