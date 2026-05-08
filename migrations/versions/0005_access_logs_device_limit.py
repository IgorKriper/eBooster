"""access logs device limit payment ids

Revision ID: 0005_access_logs_device_limit
Revises: 0004_user_connected_at
Create Date: 2026-05-02 08:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_access_logs_device_limit"
down_revision = "0004_user_connected_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE payments SET status = 'paid' WHERE status = 'succeeded'")
    op.execute("UPDATE payments SET status = 'cancelled' WHERE status = 'canceled'")
    op.add_column("users", sa.Column("device_limit", sa.Integer(), nullable=False, server_default="5"))
    op.add_column("payments", sa.Column("provider_payment_id", sa.String(length=255), nullable=True))
    op.execute("UPDATE payments SET provider_payment_id = external_id WHERE external_id IS NOT NULL")
    op.create_unique_constraint("uq_payments_provider_payment_id", "payments", ["provider_payment_id"])
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_system_logs_user_id", "system_logs", ["user_id"])
    op.create_index("ix_system_logs_event", "system_logs", ["event"])
    op.create_table(
        "admin_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_admin_logs_admin_id", "admin_logs", ["admin_id"])
    op.create_index("ix_admin_logs_action", "admin_logs", ["action"])


def downgrade() -> None:
    op.drop_index("ix_admin_logs_action", table_name="admin_logs")
    op.drop_index("ix_admin_logs_admin_id", table_name="admin_logs")
    op.drop_table("admin_logs")
    op.drop_index("ix_system_logs_event", table_name="system_logs")
    op.drop_index("ix_system_logs_user_id", table_name="system_logs")
    op.drop_table("system_logs")
    op.drop_constraint("uq_payments_provider_payment_id", "payments", type_="unique")
    op.drop_column("payments", "provider_payment_id")
    op.drop_column("users", "device_limit")
