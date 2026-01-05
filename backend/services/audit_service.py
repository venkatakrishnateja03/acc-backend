from sqlalchemy.orm import Session
from models.audit import AuditLog


def log_event(db: Session, *, workspace_id: int | None, actor_id: int | None, action: str, detail: str | None = None) -> None:
    entry = AuditLog(workspace_id=workspace_id, actor_id=actor_id, action=action, detail=detail)
    db.add(entry)
    db.commit()
