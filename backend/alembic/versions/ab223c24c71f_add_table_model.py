"""add_table_model

Revision ID: ab223c24c71f
Revises: d6e7f8a9b0c1
Create Date: 2026-01-05 11:15:41.069679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ab223c24c71f'
down_revision: Union[str, Sequence[str], None] = 'd6e7f8a9b0c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("owner_id",sa.Integer(),sa.ForeignKey("users.id", ondelete="CASCADE"),nullable=False),
        # sa.Column("workspace_id",sa.Integer(),sa.ForeignKey("workspaces.id", ondelete="CASCADE"),nullable=True),
    )

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role",sa.String(20),nullable=False,server_default="member"),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )
    op.create_table(
    "team_workspaces",
    sa.Column("id", sa.Integer(), primary_key=True),
    sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
    sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    sa.UniqueConstraint("team_id", "workspace_id", name="uq_team_workspace"),)


def downgrade() -> None:
    op.drop_table("team_members")
    op.drop_table("teams")
    op.drop_table("team_workspaces")