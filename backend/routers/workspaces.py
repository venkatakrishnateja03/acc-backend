from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.workspace import Workspace, WorkspaceMember
from models.user import User
import re

from pydantic import BaseModel
from core.schemas import MemberResponse


class CreateWorkspaceRequest(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: int
    name: str


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: CreateWorkspaceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = Workspace(name=payload.name)
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # add creator as OWNER
    member = WorkspaceMember(workspace_id=ws.id, user_id=current_user.id, role="owner")
    db.add(member)
    db.commit()

    return ws


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # list workspaces current user belongs to
    rows = (
        db.query(Workspace)
        .join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id)
        .filter(WorkspaceMember.user_id == current_user.id)
        .all()
    )
    return rows


# ---------------------------
# Members management
# ---------------------------
class AddMemberRequest(BaseModel):
    user_id: int
    role: str


@router.get("/{workspace_id}/members")
def list_members(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                      db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
) -> list[MemberResponse]:
    # Return member rows augmented with username/email for frontend display
    members = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id).all()
    def _resolve_avatar(val: str | None) -> str | None:
        if not val:
            return None
        m = re.match(r"^media:(\d+):(\d+)$", val)
        if m:
            ws, mid = m.group(1), m.group(2)
            return f"/workspaces/{ws}/media/{mid}/download"
        return val

    result = []
    for m in members:
        u = getattr(m, "user", None)
        avatar = None
        if u:
            for k in ("avatar_url", "avatar", "avatarUrl", "profile_image_url"):
                v = getattr(u, k, None)
                if v:
                    avatar = _resolve_avatar(v)
                    break
        result.append({
            "id": m.id,
            "workspace_id": m.workspace_id,
            "user_id": m.user_id,
            "role": m.role,
            "username": getattr(u, "username", None),
            "email": getattr(u, "email", None),
            "avatar_url": avatar,
        })
    return result


@router.post("/{workspace_id}/members", status_code=201, response_model=MemberResponse)
def add_member_endpoint(
    workspace_id: int,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                                            db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
):
    # Only OWNER or ADMIN can manage members
    if caller_member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Admin cannot assign OWNER
    if payload.role.lower() == "owner" and caller_member.role != "owner":
        raise HTTPException(status_code=403, detail="Only OWNER can assign OWNER role")

    # Prevent duplicates
    existing = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=payload.user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already a member")

    member = WorkspaceMember(workspace_id=workspace_id, user_id=payload.user_id, role=payload.role.lower())
    db.add(member)
    db.commit()
    db.refresh(member)

    # TODO: create audit log (write-only)

    return {
        "id": member.id,
        "workspace_id": member.workspace_id,
        "user_id": member.user_id,
        "role": member.role,
        "username": getattr(member.user, "username", None),
        "email": getattr(member.user, "email", None),
        "avatar_url": next((getattr(member.user, k, None) for k in ("avatar_url", "avatar", "avatarUrl", "profile_image_url") if getattr(member.user, k, None)), None),
    }


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberResponse)
def patch_member(
    workspace_id: int,
    user_id: int,
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                                            db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
):
    if caller_member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    target = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    # Only OWNER can assign OWNER
    if payload.role.lower() == "owner" and caller_member.role != "owner":
        raise HTTPException(status_code=403, detail="Only OWNER can assign OWNER role")

    target.role = payload.role.lower()
    db.commit()
    db.refresh(target)

    # TODO: audit log role change
    return {
        "id": target.id,
        "workspace_id": target.workspace_id,
        "user_id": target.user_id,
        "role": target.role,
        "username": getattr(target.user, "username", None),
        "email": getattr(target.user, "email", None),
        "avatar_url": next((getattr(target.user, k, None) for k in ("avatar_url", "avatar", "avatarUrl", "profile_image_url") if getattr(target.user, k, None)), None),
    }


@router.delete("/{workspace_id}/members/{user_id}")
def delete_member(
    workspace_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                                            db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
):
    if caller_member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    target = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    # Only OWNER can remove OWNER
    if target.role == "owner" and caller_member.role != "owner":
        raise HTTPException(status_code=403, detail="Only OWNER can remove OWNER")

    # Prevent removing last owner
    if target.role == "owner":
        owners = db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, role="owner").count()
        if owners <= 1 and user_id == target.user_id:
            raise HTTPException(status_code=400, detail="Cannot remove last OWNER")

    db.delete(target)
    db.commit()

    # TODO: audit log member removal
    try:
        from services.audit_service import log_event

        log_event(db, workspace_id=workspace_id, actor_id=current_user.id, action="member.remove", detail=str(user_id))
    except Exception:
        pass
    return {"detail": "Member removed"}


# ---------------------------
# Workspace settings
# ---------------------------


class WorkspaceUpdateRequest(BaseModel):
    name: str


@router.patch("/{workspace_id}")
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                                            db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
):
    if caller_member.role != "owner":
        raise HTTPException(status_code=403, detail="Only OWNER can modify workspace settings")

    ws = db.query(Workspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws.name = payload.name
    db.commit()
    db.refresh(ws)
    return ws


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    caller_member: WorkspaceMember = Depends(lambda workspace_id, db=Depends(get_db), current_user=Depends(get_current_user):
                                            db.query(WorkspaceMember).filter_by(workspace_id=workspace_id, user_id=current_user.id).first() or (_ for _ in ()).throw(HTTPException(status_code=403, detail="Not a workspace member"))),
):
    if caller_member.role != "owner":
        raise HTTPException(status_code=403, detail="Only OWNER can delete workspace")

    ws = db.query(Workspace).filter_by(id=workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # cascade delete (DB FK cascade set on models) — perform soft-delete if desired
    db.delete(ws)
    db.commit()
    try:
        from services.audit_service import log_event

        log_event(db, workspace_id=workspace_id, actor_id=current_user.id, action="workspace.delete", detail=str(workspace_id))
    except Exception:
        pass
    return {"detail": "Workspace deleted"}
