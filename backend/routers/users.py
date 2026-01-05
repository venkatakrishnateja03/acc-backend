from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.workspace import Workspace, WorkspaceMember
from core.schemas import UserProfileResponse, UserProfileUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
def get_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Build recent_workspaces: last 5 workspaces by membership id
    mrows = (
        db.query(WorkspaceMember)
        .filter(WorkspaceMember.user_id == current_user.id)
        .order_by(WorkspaceMember.id.desc())
        .limit(5)
        .all()
    )
    recent = []
    if mrows:
        ws_ids = [m.workspace_id for m in mrows]
        ws_rows = db.query(Workspace).filter(Workspace.id.in_(ws_ids)).all()
        ws_map = {w.id: w for w in ws_rows}
        for m in mrows:
            w = ws_map.get(m.workspace_id)
            if w:
                recent.append({"id": w.id, "name": w.name, "role": m.role})

    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "first_name": getattr(current_user, "first_name", None),
        "last_name": getattr(current_user, "last_name", None),
        "avatar_url": getattr(current_user, "avatar_url", None),
        "date_of_birth": getattr(current_user, "date_of_birth", None),
        "bio": getattr(current_user, "bio", None),
        "created_at": current_user.created_at,
        "recent_workspaces": recent,
    }


@router.patch("/me", response_model=UserProfileResponse)
def patch_me(payload: UserProfileUpdateRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validate username uniqueness if present
    if payload.username and payload.username != current_user.username:
        exists = db.query(User).filter(User.username == payload.username).filter(User.id != current_user.id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Username already exists")

    # Update allowed profile fields only
    if payload.username is not None:
        current_user.username = payload.username
    if payload.first_name is not None:
        current_user.first_name = payload.first_name
    if payload.last_name is not None:
        current_user.last_name = payload.last_name
    if payload.avatar_url is not None:
        current_user.avatar_url = payload.avatar_url
    if payload.date_of_birth is not None:
        # expect YYYY-MM-DD string; DB will accept date parsing by SQLAlchemy
        current_user.date_of_birth = payload.date_of_birth
    if payload.bio is not None:
        current_user.bio = payload.bio

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # reuse GET logic for recent workspaces
    return get_me(db=db, current_user=current_user)
