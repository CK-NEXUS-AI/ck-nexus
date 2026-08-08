from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from services.billing.billing_events import BillingEventService
from services.billing.plans import (
    PlanTier,
    get_plan,
    get_plan_by_stripe_price_id,
    is_within_limits,
)
from services.billing.subscription_manager import (
    SubscriptionManager,
    SubscriptionStatus,
)

# --- plans ---


def test_get_plan_starter():
    plan = get_plan(PlanTier.STARTER)
    assert plan.price_thb == 990
    assert plan.max_agents == 3


def test_get_plan_pro():
    plan = get_plan(PlanTier.PRO)
    assert plan.price_thb == 4_900
    assert plan.max_agents == 20


def test_get_plan_enterprise_unlimited():
    plan = get_plan(PlanTier.ENTERPRISE)
    assert plan.max_agents == -1
    assert is_within_limits(plan, "agents", 999_999) is True


def test_get_plan_by_stripe_price_id():
    plan = get_plan_by_stripe_price_id("price_pro_monthly")
    assert plan is not None
    assert plan.tier == PlanTier.PRO


def test_get_plan_by_unknown_price_id():
    plan = get_plan_by_stripe_price_id("price_unknown")
    assert plan is None


def test_within_limits_starter():
    plan = get_plan(PlanTier.STARTER)
    assert is_within_limits(plan, "agents", 2) is True
    assert is_within_limits(plan, "agents", 3) is False


# --- subscription manager ---


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest.mark.asyncio
async def test_subscription_upsert_create(db_session):
    manager = SubscriptionManager(db=db_session)
    now = datetime.now(UTC)

    sub = await manager.upsert(
        tenant_id="tenant-1",
        stripe_customer_id="cus_123",
        stripe_subscription_id="sub_123",
        stripe_price_id="price_pro_monthly",
        plan_tier="pro",
        status="active",
        current_period_start=now,
        current_period_end=now,
    )

    assert sub.tenant_id == "tenant-1"
    assert sub.status == "active"


@pytest.mark.asyncio
async def test_subscription_suspend_activate(db_session):
    manager = SubscriptionManager(db=db_session)
    now = datetime.now(UTC)

    await manager.upsert(
        tenant_id="tenant-2",
        stripe_customer_id="cus_456",
        stripe_subscription_id="sub_456",
        stripe_price_id="price_starter_monthly",
        plan_tier="starter",
        status="active",
        current_period_start=now,
        current_period_end=now,
    )

    await manager.suspend("tenant-2")
    sub = await manager.get_by_tenant("tenant-2")
    assert sub.status == SubscriptionStatus.SUSPENDED

    await manager.activate("tenant-2")
    sub = await manager.get_by_tenant("tenant-2")
    assert sub.status == SubscriptionStatus.ACTIVE


# --- billing events ---


@pytest.mark.asyncio
async def test_billing_event_record(db_session):
    service = BillingEventService(db=db_session)

    event = await service.record(
        tenant_id="tenant-3",
        event_type="invoice.paid",
        payload={"invoice_id": "inv_123"},
    )

    assert event.id is not None
    assert event.tenant_id == "tenant-3"
    assert event.event_type == "invoice.paid"
    assert event.payload["invoice_id"] == "inv_123"
