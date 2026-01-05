from db.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from models.team_member import TeamMember
from routers.auth import get_current_user
from sqlalchemy.orm import Session
from models.user import User
def require_team_member(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamMember:
    member = (
        db.query(TeamMember)
        .filter_by(team_id=team_id, user_id=current_user.id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Not a team member")
    return member
