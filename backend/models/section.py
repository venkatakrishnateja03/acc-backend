from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db.database import Base


class WorkspaceSection(Base):
    """Sprint-2 foundation: grouping for media/docs inside a workspace.

    Minimal model now; will be extended later with permissions and ordering.
    """
    __tablename__ = "workspace_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # TODO: add ordering, parent-child sections, and relationship to Media/Docs
