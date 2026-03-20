"""Add unique constraint for users platform identity.

Revision ID: 002_users_platform_unique
Revises: 001_initial
Create Date: 2026-03-21
"""

from alembic import op


revision = "002_users_platform_unique"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_users_platform_platform_user_id",
        "users",
        ["platform", "platform_user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_users_platform_platform_user_id",
        "users",
        type_="unique",
    )
