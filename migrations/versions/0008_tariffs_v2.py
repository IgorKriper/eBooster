"""TZ Executive Summary: Solo/Plus/Family tariffs (1/3/12 months)

Revision ID: 0008_tariffs_v2
Revises: 0007_devices_and_branding
Create Date: 2026-05-08

Additive migration:
- Adds plans.tariff_code (solo/plus/family/legacy_plus_5)
- Adds plans.period_months (1/3/12 for subscriptions, NULL for device packs)
- Adds plans.slot_limit (number of devices granted by a subscription tariff)
- Backfills existing month_*/device_pack_* rows with the matching Solo metadata
- Inserts Plus (349/949/3290) and Family (590/1590/5490) tariff rows
- Inserts the internal legacy_plus_5 plan used for legacy migrations

Existing payments keep their plan_id refs intact — no rows are deleted.
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_tariffs_v2"
down_revision = "0007_devices_and_branding"
branch_labels = None
depends_on = None


SUBSCRIPTION_KIND = "subscription"
DEVICE_PACK_KIND = "device_pack"


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column("tariff_code", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column("period_months", sa.Integer(), nullable=True),
    )
    op.add_column(
        "plans",
        sa.Column(
            "slot_limit",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_index("ix_plans_tariff_code", "plans", ["tariff_code"])

    bind = op.get_bind()

    # Backfill legacy month_* rows -> Solo at 1/3/12 months (prices already match).
    # Existing payments keep pointing to these rows; we just enrich metadata.
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', period_months=1, slot_limit=2, "
            "title='Solo · 1 мес', is_active=TRUE WHERE slug='month_1'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', period_months=3, slot_limit=2, "
            "title='Solo · 3 мес', is_active=TRUE WHERE slug='month_3'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', period_months=12, slot_limit=2, "
            "title='Solo · 12 мес', is_active=TRUE WHERE slug='month_12'"
        )
    )

    # Solo addons (only Solo gets +N devices).
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', slot_limit=0, "
            "title='+1 устройство', is_active=TRUE WHERE slug='device_pack_1'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', slot_limit=0, "
            "title='+2 устройства', is_active=TRUE WHERE slug='device_pack_2'"
        )
    )
    bind.execute(
        sa.text(
            "UPDATE plans SET tariff_code='solo', slot_limit=0, "
            "title='+3 устройства', is_active=TRUE WHERE slug='device_pack_3'"
        )
    )

    # Insert Plus (slot_limit=5).
    _seed_plan(bind, slug="plus_1m", title="Plus · 1 мес",
               days=30, price=349, period=1, kind=SUBSCRIPTION_KIND,
               tariff_code="plus", slot_limit=5)
    _seed_plan(bind, slug="plus_3m", title="Plus · 3 мес",
               days=90, price=949, period=3, kind=SUBSCRIPTION_KIND,
               tariff_code="plus", slot_limit=5)
    _seed_plan(bind, slug="plus_12m", title="Plus · 12 мес",
               days=365, price=3290, period=12, kind=SUBSCRIPTION_KIND,
               tariff_code="plus", slot_limit=5)

    # Insert Family (slot_limit=10).
    _seed_plan(bind, slug="family_1m", title="Family · 1 мес",
               days=30, price=590, period=1, kind=SUBSCRIPTION_KIND,
               tariff_code="family", slot_limit=10)
    _seed_plan(bind, slug="family_3m", title="Family · 3 мес",
               days=90, price=1590, period=3, kind=SUBSCRIPTION_KIND,
               tariff_code="family", slot_limit=10)
    _seed_plan(bind, slug="family_12m", title="Family · 12 мес",
               days=365, price=5490, period=12, kind=SUBSCRIPTION_KIND,
               tariff_code="family", slot_limit=10)

    # Internal legacy plan — never shown in pickers, used to keep historical
    # users on a 5-device limit as their old subscription period winds down.
    _seed_plan(bind, slug="legacy_plus_5",
               title="Legacy (5 устройств)",
               days=0, price=0, period=None, kind=SUBSCRIPTION_KIND,
               tariff_code="legacy_plus_5", slot_limit=5,
               is_active=False)


def _seed_plan(
    bind,
    *,
    slug: str,
    title: str,
    days: int,
    price: int,
    period: int | None,
    kind: str,
    tariff_code: str,
    slot_limit: int,
    is_active: bool = True,
) -> None:
    existing = bind.execute(
        sa.text("SELECT id FROM plans WHERE slug=:slug"),
        {"slug": slug},
    ).first()
    if existing is None:
        bind.execute(
            sa.text(
                "INSERT INTO plans (slug, title, duration_days, price_rub, "
                "is_active, kind, bonus_devices, tariff_code, period_months, "
                "slot_limit) VALUES (:slug, :title, :days, :price, :is_active, "
                ":kind, 0, :tariff_code, :period, :slot_limit)"
            ),
            {
                "slug": slug,
                "title": title,
                "days": days,
                "price": price,
                "is_active": is_active,
                "kind": kind,
                "tariff_code": tariff_code,
                "period": period,
                "slot_limit": slot_limit,
            },
        )
    else:
        bind.execute(
            sa.text(
                "UPDATE plans SET title=:title, duration_days=:days, "
                "price_rub=:price, is_active=:is_active, kind=:kind, "
                "tariff_code=:tariff_code, period_months=:period, "
                "slot_limit=:slot_limit WHERE slug=:slug"
            ),
            {
                "slug": slug,
                "title": title,
                "days": days,
                "price": price,
                "is_active": is_active,
                "kind": kind,
                "tariff_code": tariff_code,
                "period": period,
                "slot_limit": slot_limit,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_plans_tariff_code", table_name="plans")
    op.drop_column("plans", "slot_limit")
    op.drop_column("plans", "period_months")
    op.drop_column("plans", "tariff_code")
