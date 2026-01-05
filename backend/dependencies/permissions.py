from typing import Callable, List

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.workspace import WorkspaceMember
from models.user import User


def require_workspace_member(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceMember:
    """Ensure the current user is a member of the workspace.

    Returns the WorkspaceMember row for downstream use.
    """
    member = (
        db.query(WorkspaceMember)
        .filter_by(workspace_id=workspace_id, user_id=current_user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a workspace member")
    return member


def require_workspace_role(allowed_roles: List[str]) -> Callable:
    """Factory that returns a dependency verifying the member role is allowed.

    Usage in routes:
        Depends(require_workspace_role(["OWNER","ADMIN","EDITOR"]))
    """

    def _dependency(
        workspace_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> WorkspaceMember:
        member = (
            db.query(WorkspaceMember)
            .filter_by(workspace_id=workspace_id, user_id=current_user.id)
            .first()
        )
        if not member:
            raise HTTPException(status_code=403, detail="Not a workspace member")
        # Normalize role strings to lowercase so DB-stored values (e.g. "owner")
        # compare correctly against allowed roles regardless of case.
        normalized_allowed = {r.strip().lower() for r in allowed_roles}
        member_role = (member.role or "").strip().lower()
        if member_role not in normalized_allowed:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return member

    return _dependency
