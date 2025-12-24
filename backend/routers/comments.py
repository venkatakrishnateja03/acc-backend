from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.comment import Comment
from dependencies.permissions import require_workspace_member, require_workspace_role
from core.schemas import CommentCreateRequest, CommentResponse

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
    return comment


@router.get("", response_model=list[CommentResponse])
def list_comments(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    rows = db.query(Comment).filter_by(workspace_id=workspace_id).all()
    return rows


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
