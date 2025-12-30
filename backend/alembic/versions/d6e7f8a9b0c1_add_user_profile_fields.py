"""add user profile fields

Revision ID: d6e7f8a9b0c1
Revises: c4d5e6f7a8b9
Create Date: 2025-12-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6e7f8a9b0c1'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('first_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('date_of_birth', sa.DATE(), nullable=True))
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'bio')
    op.drop_column('users', 'date_of_birth')
    op.drop_column('users', 'avatar_url')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')
