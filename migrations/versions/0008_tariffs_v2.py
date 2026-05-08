"""tariffs v2: add plans.slot_devices for Solo/Plus/Family

Revision ID: 0008_tariffs_v2
Revises: 0007_devices_and_branding
Create Date: 2026-05-08

Additive only. No drops. Existing plans get slot_devices=0 by default and
will be deactivated by the seed step (services/plans.seed_plans), but the
rows stay so historical Payment.plan_id references remain valid.
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_tariffs_v2"
down_revision = "0007_devices_and_branding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "slot_devices",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("plans", "slot_devices")
