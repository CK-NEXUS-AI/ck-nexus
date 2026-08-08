from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from opentelemetry import trace
from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

tracer = trace.get_tracer(__name__)


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"
    SUSPENDED = "suspended"


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True, unique=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(128), index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(128), index=True)
    stripe_price_id: Mapped[str] = mapped_column(String(128))
    plan_tier: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64), default=SubscriptionStatus.ACTIVE)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class SubscriptionManager:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert(
        self,
        tenant_id: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        plan_tier: str,
        status: str,
        current_period_start: datetime,
        current_period_end: datetime,
    ) -> TenantSubscription:
        with tracer.start_as_current_span("subscription.upsert") as span:
            span.set_attribute("tenant.id", tenant_id)
            span.set_attribute("plan.tier", plan_tier)

            result = await self.db.execute(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
            )
            sub = result.scalar_one_or_none()

            if sub is None:
                sub = TenantSubscription(tenant_id=tenant_id)
                self.db.add(sub)

            sub.stripe_customer_id = stripe_customer_id
            sub.stripe_subscription_id = stripe_subscription_id
            sub.stripe_price_id = stripe_price_id
            sub.plan_tier = plan_tier
            sub.status = status
            sub.current_period_start = current_period_start
            sub.current_period_end = current_period_end

            await self.db.commit()
            await self.db.refresh(sub)

            return sub

    async def get_by_tenant(
        self,
        tenant_id: str,
    ) -> TenantSubscription | None:
        result = await self.db.execute(
            select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
        )
        return result.scalar_one_or_none()

    async def suspend(self, tenant_id: str) -> None:
        sub = await self.get_by_tenant(tenant_id)
        if sub:
            sub.status = SubscriptionStatus.SUSPENDED
            await self.db.commit()

    async def activate(self, tenant_id: str) -> None:
        sub = await self.get_by_tenant(tenant_id)
        if sub:
            sub.status = SubscriptionStatus.ACTIVE
            await self.db.commit()
