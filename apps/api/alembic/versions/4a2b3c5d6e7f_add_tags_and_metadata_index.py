"""Add tags column to documents and GIN index on document_chunks.meta_data.

Revision ID: 4a2b3c5d6e7f
Revises: 6f1d7e5a6b2c
Create Date: 2026-07-15 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "4a2b3c5d6e7f"
down_revision: str | None = "6f1d7e5a6b2c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"))
    op.create_index("ix_documents_tags", "documents", ["tags"], postgresql_using="gin")
    op.create_index("ix_document_chunks_meta_data", "document_chunks", ["meta_data"], postgresql_using="gin")


def downgrade() -> None:
    op.drop_index("ix_document_chunks_meta_data")
    op.drop_index("ix_documents_tags")
    op.drop_column("documents", "tags")
