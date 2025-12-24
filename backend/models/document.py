from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, func, Text
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional reference to a Media row when the document is file-backed.
    media_id: Mapped[int | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationship to optional file-backed media
    media = None

    # TODO: store PDFs encrypted in files/ and refer by stored_filename when doc_type == 'pdf'

