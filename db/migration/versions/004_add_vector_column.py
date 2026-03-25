"""Миграция: добавить колонку embedding_vector для pgvector.

Revision ID: 004_add_vector_column
Revises: 003_users_ts_defaults
Create Date: 2026-03-24
"""

from alembic import op


revision = "004_add_vector_column"
down_revision = "003_users_ts_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE embeddings 
        ADD COLUMN embedding_vector vector(1024)
    """)

    op.execute("""
        UPDATE embeddings 
        SET embedding_vector = 
            (SELECT array_agg(elem::float) 
             FROM jsonb_array_elements_text(embedding::jsonb) AS elem)
        WHERE embedding IS NOT NULL
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embeddings_vector 
        ON embeddings USING ivfflat (embedding_vector vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector")
    op.execute("ALTER TABLE embeddings DROP COLUMN IF EXISTS embedding_vector")
