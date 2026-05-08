"""user connected timestamp

Revision ID: 0004_user_connected_at
Revises: 0003_notifications_log
Create Date: 2026-05-02 07:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_user_connected_at"
down_revision = "0003_notifications_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "connected_at")
