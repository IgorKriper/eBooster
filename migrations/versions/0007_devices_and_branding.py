"""device packs branding and connect tokens

Revision ID: 0007_devices_and_branding
Revises: 0006_server_load_states
Create Date: 2026-05-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_devices_and_branding"
down_revision = "0006_server_load_states"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "kind",
            sa.String(length=32),
            nullable=False,
            server_default="subscription",
        ),
    )
    op.add_column(
        "plans",
        sa.Column(
            "bonus_devices",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_table(
        "connect_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("token", name="uq_connect_tokens_token"),
    )
    op.create_index("ix_connect_tokens_user_id", "connect_tokens", ["user_id"])
    op.create_index("ix_connect_tokens_token", "connect_tokens", ["token"])


def downgrade() -> None:
    op.drop_index("ix_connect_tokens_token", table_name="connect_tokens")
    op.drop_index("ix_connect_tokens_user_id", table_name="connect_tokens")
    op.drop_table("connect_tokens")
    op.drop_column("plans", "bonus_devices")
    op.drop_column("plans", "kind")
