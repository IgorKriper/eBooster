"""server load states

Revision ID: 0006_server_load_states
Revises: 0005_access_logs_device_limit
Create Date: 2026-05-03
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_server_load_states"
down_revision = "0005_access_logs_device_limit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "server_load_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("capacity_mbps", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("load_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rx_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tx_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_sample_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alert_level", sa.String(length=16), nullable=True),
        sa.Column("alert_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("code", name="uq_server_load_states_code"),
    )
    op.create_index("ix_server_load_states_code", "server_load_states", ["code"])
    op.create_index("ix_server_load_states_host", "server_load_states", ["host"])


def downgrade() -> None:
    op.drop_index("ix_server_load_states_host", table_name="server_load_states")
    op.drop_index("ix_server_load_states_code", table_name="server_load_states")
    op.drop_table("server_load_states")
