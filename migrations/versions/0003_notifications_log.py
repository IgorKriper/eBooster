"""notifications log

Revision ID: 0003_notifications_log
Revises: 0002_referrals_notifications
Create Date: 2026-05-02 06:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_notifications_log"
down_revision = "0002_referrals_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "type", name="uq_notifications_log_user_type"),
    )
    op.create_index("ix_notifications_log_user_id", "notifications_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_log_user_id", table_name="notifications_log")
    op.drop_table("notifications_log")
