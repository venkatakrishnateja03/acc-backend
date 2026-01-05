from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.workspace import WorkspaceMember, WorkspaceRole, Workspace


def add_member(db: Session, workspace_id: int, user_id: int, role: str, actor_id: int) -> WorkspaceMember:
    # normalize role
    role = role.lower()
    if role not in {r.value for r in WorkspaceRole}:
        raise HTTPException(status_code=400, detail="Invalid role")

    # prevent duplicate
    existing = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already a member")

    # if assigning owner, only actor OWNER allowed — caller must enforce
    member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def change_member_role(db: Session, workspace_id: int, user_id: int, new_role: str, actor_id: int) -> WorkspaceMember:
    new_role = new_role.lower()
    if new_role not in {r.value for r in WorkspaceRole}:
        raise HTTPException(status_code=400, detail="Invalid role")

    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = new_role
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, workspace_id: int, user_id: int, actor_id: int) -> None:
    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
