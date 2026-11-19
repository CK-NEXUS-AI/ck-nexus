from __future__ import annotations

from datetime import UTC, datetime

from opentelemetry import trace
from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from services.billing.billing_events import BillingEventService
from services.billing.stripe_client import StripeClient
from services.billing.subscription_manager import SubscriptionManager

tracer = trace.get_tracer(__name__)

HANDLED_EVENTS = {
    "checkout.session.completed",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
}


class ProcessedWebhookEvent(Base):
    __tablename__ = "processed_webhook_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stripe_event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class WebhookHandler:
    def __init__(
        self,
        db: AsyncSession,
        stripe_client: StripeClient,
        subscription_manager: SubscriptionManager,
        billing_events: BillingEventService,
        webhook_secret: str,
    ) -> None:
        self.db = db
        self.stripe = stripe_client
        self.subscriptions = subscription_manager
        self.billing_events = billing_events
        self.webhook_secret = webhook_secret

    async def _is_already_processed(self, event_id: str) -> bool:
        result = await self.db.execute(
            select(ProcessedWebhookEvent).where(ProcessedWebhookEvent.stripe_event_id == event_id)
        )
        return result.scalar_one_or_none() is not None

    async def _mark_processed(self, event_id: str, event_type: str) -> None:
        self.db.add(
            ProcessedWebhookEvent(
                stripe_event_id=event_id,
                event_type=event_type,
            )
        )
        await self.db.commit()

    async def handle(self, payload: bytes, sig_header: str) -> dict:
        with tracer.start_as_current_span("webhook.handle") as span:
            event = self.stripe.construct_webhook_event(
                payload=payload,
                sig_header=sig_header,
                webhook_secret=self.webhook_secret,
            )

            span.set_attribute("stripe.event_id", event.id)
            span.set_attribute("stripe.event_type", event.type)

            if event.type not in HANDLED_EVENTS:
                return {"status": "ignored", "event_type": event.type}

            if await self._is_already_processed(event.id):
                return {"status": "duplicate", "event_id": event.id}

            await self._dispatch(event)
            await self._mark_processed(event.id, event.type)

            return {"status": "processed", "event_id": event.id}

    async def _dispatch(self, event) -> None:
        data = event.data.object

        if event.type == "checkout.session.completed":
            await self._on_checkout_completed(data)

        elif event.type == "invoice.paid":
            await self._on_invoice_paid(data)

        elif event.type == "invoice.payment_failed":
            await self._on_invoice_payment_failed(data)

        elif event.type in (
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            await self._on_subscription_changed(data)

    async def _on_checkout_completed(self, session) -> None:
        tenant_id = session.get("metadata", {}).get("tenant_id", "")
        subscription_id = session.get("subscription", "")

        if not tenant_id or not subscription_id:
            return

        sub = await self.stripe.retrieve_subscription(subscription_id)

        await self.subscriptions.upsert(
            tenant_id=tenant_id,
            stripe_customer_id=session.get("customer", ""),
            stripe_subscription_id=subscription_id,
            stripe_price_id=sub["items"]["data"][0]["price"]["id"],
            plan_tier=sub["metadata"].get("plan_tier", "starter"),
            status="active",
            current_period_start=datetime.fromtimestamp(sub["current_period_start"], tz=UTC),
            current_period_end=datetime.fromtimestamp(sub["current_period_end"], tz=UTC),
        )

        await self.billing_events.record(
            tenant_id=tenant_id,
            event_type="checkout.session.completed",
            payload={"subscription_id": subscription_id},
        )

    async def _on_invoice_paid(self, invoice) -> None:
        tenant_id = invoice.get("subscription_details", {}).get("metadata", {}).get("tenant_id", "")

        if tenant_id:
            await self.subscriptions.activate(tenant_id)
            await self.billing_events.record(
                tenant_id=tenant_id,
                event_type="invoice.paid",
                payload={"invoice_id": invoice.get("id")},
            )

    async def _on_invoice_payment_failed(self, invoice) -> None:
        tenant_id = invoice.get("subscription_details", {}).get("metadata", {}).get("tenant_id", "")

        if tenant_id:
            await self.subscriptions.suspend(tenant_id)
            await self.billing_events.record(
                tenant_id=tenant_id,
                event_type="invoice.payment_failed",
                payload={"invoice_id": invoice.get("id")},
            )

    async def _on_subscription_changed(self, subscription) -> None:
        tenant_id = subscription.get("metadata", {}).get("tenant_id", "")

        if tenant_id:
            await self.subscriptions.upsert(
                tenant_id=tenant_id,
                stripe_customer_id=subscription.get("customer", ""),
                stripe_subscription_id=subscription.get("id", ""),
                stripe_price_id=subscription["items"]["data"][0]["price"]["id"],
                plan_tier=subscription["metadata"].get("plan_tier", "starter"),
                status=subscription.get("status", "active"),
                current_period_start=datetime.fromtimestamp(
                    subscription["current_period_start"], tz=UTC
                ),
                current_period_end=datetime.fromtimestamp(
                    subscription["current_period_end"], tz=UTC
                ),
            )
