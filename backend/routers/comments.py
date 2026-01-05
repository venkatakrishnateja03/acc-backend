from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.comment import Comment
from dependencies.permissions import require_workspace_member, require_workspace_role
from core.schemas import CommentCreateRequest, CommentResponse
import re

router = APIRouter(prefix="/workspaces/{workspace_id}/comments", tags=["comments"])


@router.post("", response_model=CommentResponse)
def create_comment(
    workspace_id: int,
    payload: CommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    comment = Comment(
        workspace_id=workspace_id,
        author_id=current_user.id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        body=payload.body,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    # fetch author info explicitly to avoid ORM mapper ordering issues
    author = None
    if comment.author_id is not None:
        author = db.query(User).filter_by(id=comment.author_id).first()
    def _resolve_avatar(val: str | None) -> str | None:
        if not val:
            return None
        m = re.match(r"^media:(\d+):(\d+)$", val)
        if m:
            ws, mid = m.group(1), m.group(2)
            return f"/workspaces/{ws}/media/{mid}/download"
        return val

    avatar = None
    if author:
        for k in ("avatar_url", "avatar", "avatarUrl", "profile_image_url"):
            v = getattr(author, k, None)
            if v:
                avatar = _resolve_avatar(v)
                break

    return {
        "id": comment.id,
        "workspace_id": comment.workspace_id,
        "author_id": comment.author_id,
        "author_username": getattr(author, "username", None) if author else None,
        "author_email": getattr(author, "email", None) if author else None,
        "author_avatar_url": avatar,
        "target_type": comment.target_type,
        "target_id": comment.target_id,
        "body": comment.body,
        "created_at": comment.created_at,
    }


@router.get("", response_model=list[CommentResponse])
def list_comments(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    rows = db.query(Comment).filter_by(workspace_id=workspace_id).all()
    # bulk-load user info to avoid N+1 queries
    author_ids = {c.author_id for c in rows if c.author_id}
    users = {}
    if author_ids:
        urows = db.query(User).filter(User.id.in_(list(author_ids))).all()
        users = {u.id: u for u in urows}

    result = []
    for c in rows:
        a = users.get(c.author_id)
        # resolve avatar from a few possible fields and support media:<ws>:<id> refs
        def _resolve_avatar(val: str | None) -> str | None:
            if not val:
                return None
            m = re.match(r"^media:(\d+):(\d+)$", val)
            if m:
                ws, mid = m.group(1), m.group(2)
                return f"/workspaces/{ws}/media/{mid}/download"
            return val

        avatar = None
        if a:
            for k in ("avatar_url", "avatar", "avatarUrl", "profile_image_url"):
                v = getattr(a, k, None)
                if v:
                    avatar = _resolve_avatar(v)
                    break

        result.append({
            "id": c.id,
            "workspace_id": c.workspace_id,
            "author_id": c.author_id,
            "author_username": getattr(a, "username", None) if a else None,
            "author_email": getattr(a, "email", None) if a else None,
            "author_avatar_url": avatar,
            "target_type": c.target_type,
            "target_id": c.target_id,
            "body": c.body,
            "created_at": c.created_at,
        })
    return result


@router.delete("/{comment_id}")
def delete_comment(
    workspace_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    member = Depends(require_workspace_member),
):
    comment = db.query(Comment).filter_by(workspace_id=workspace_id, id=comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # allowed: author or OWNER/ADMIN
    if comment.author_id != current_user.id and member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    db.delete(comment)
    db.commit()
    return {"detail": "Comment deleted"}
