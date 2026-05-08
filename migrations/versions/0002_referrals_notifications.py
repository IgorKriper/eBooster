"""referral caps and subscription notifications

Revision ID: 0002_referrals_notifications
Revises: 0001_initial
Create Date: 2026-05-02 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_referrals_notifications"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("subscription_until_key", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "kind", "subscription_until_key", name="uq_subscription_notice"),
    )
    op.create_index("ix_subscription_notifications_user_id", "subscription_notifications", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_subscription_notifications_user_id", table_name="subscription_notifications")
    op.drop_table("subscription_notifications")
