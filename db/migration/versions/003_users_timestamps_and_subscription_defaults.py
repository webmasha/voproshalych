"""Нормализует timestamps пользователей и дефолт подписки.

Revision ID: 003_users_ts_defaults
Revises: 002_users_platform_unique
Create Date: 2026-03-21
"""

from alembic import op
import sqlalchemy as sa


revision = "003_users_ts_defaults"
down_revision = "002_users_platform_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_subscribed = false WHERE is_subscribed IS NULL")
    op.execute("UPDATE users SET created_at = now() WHERE created_at IS NULL")
    op.execute("UPDATE users SET updated_at = now() WHERE updated_at IS NULL")

    op.alter_column(
        "users",
        "is_subscribed",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "users",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "users",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "users",
        "is_subscribed",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=sa.text("false"),
    )
