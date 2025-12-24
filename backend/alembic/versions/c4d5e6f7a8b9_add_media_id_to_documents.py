"""add media_id to documents

Revision ID: c4d5e6f7a8b9
Revises: b1c2d3e4f5a6
Create Date: 2025-12-24 07:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add nullable media_id column to documents and create FK to media.id
    op.add_column('documents', sa.Column('media_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_documents_media_id'), 'documents', ['media_id'], unique=False)
    op.create_foreign_key('documents_media_id_fkey', 'documents', 'media', ['media_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('documents_media_id_fkey', 'documents', type_='foreignkey')
    op.drop_index(op.f('ix_documents_media_id'), table_name='documents')
    op.drop_column('documents', 'media_id')
