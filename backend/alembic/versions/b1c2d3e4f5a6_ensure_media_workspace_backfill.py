"""ensure media.workspace_id exists and backfill safely

Revision ID: b1c2d3e4f5a6
Revises: 8a97a99c8a6d
Create Date: 2025-12-23 07:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'b1c2d3e4f5a6'
down_revision = '8a97a99c8a6d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    cols = [c['name'] for c in inspector.get_columns('media')]

    # Add workspace_id column if it's not already present (nullable initially).
    if 'workspace_id' not in cols:
        op.add_column('media', sa.Column('workspace_id', sa.Integer(), nullable=True))

    # Backfill strategy: if there's exactly one workspace, assign all media to it.
    # This is a safe, idempotent heuristic for developer/local databases.
    count_workspaces = conn.execute(text("SELECT COUNT(*) FROM workspaces")).scalar()
    if count_workspaces == 1:
        workspace_id = conn.execute(text("SELECT id FROM workspaces LIMIT 1")).scalar()
        conn.execute(text("UPDATE media SET workspace_id = :wid WHERE workspace_id IS NULL"), {'wid': workspace_id})

    # Create foreign key if not present
    fks = [fk['constrained_columns'] for fk in inspector.get_foreign_keys('media')]
    # normalized list of fk columns
    fk_cols = [tuple(f) for f in fks]
    if ('workspace_id',) not in fk_cols:
        op.create_foreign_key(
            'media_workspace_id_fkey',
            'media', 'workspaces',
            ['workspace_id'], ['id'],
            ondelete='CASCADE'
        )

    # Create index on workspace_id if missing
    idxs = [i['column_names'] for i in inspector.get_indexes('media')]
    if ['workspace_id'] not in idxs:
        op.create_index(op.f('ix_media_workspace_id'), 'media', ['workspace_id'], unique=False)

    # Do NOT set NOT NULL here; require an explicit backfill+alter once data is validated.


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Drop FK if exists
    fks = inspector.get_foreign_keys('media')
    for fk in fks:
        if fk['referred_table'] == 'workspaces' and fk['constrained_columns'] == ['workspace_id']:
            op.drop_constraint(fk['name'], 'media', type_='foreignkey')

    # Drop index if exists
    idxs = [i['name'] for i in inspector.get_indexes('media')]
    if 'ix_media_workspace_id' in idxs:
        op.drop_index('ix_media_workspace_id', table_name='media')

    # Drop column if exists
    cols = [c['name'] for c in inspector.get_columns('media')]
    if 'workspace_id' in cols:
        op.drop_column('media', 'workspace_id')
