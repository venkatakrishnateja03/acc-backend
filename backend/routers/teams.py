from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.team import Team
from models.team_member import TeamMember
from models.workspace import WorkspaceMember
from models.user import User
from core.schemas import CreateTeamRequest, TeamResponse, TeamMemberResponse
from pydantic import BaseModel
from core.schemas import MemberResponse
from services.team_service import require_team_member
class CreateTeamRequest(BaseModel):
    name: str


class TeamResponse(BaseModel):
    id: int
    name: str
router = APIRouter(prefix="/teams", tags=["teams"])

@router.post(
    "",
    response_model=TeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_team(
    payload: CreateTeamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = Team(name=payload.name,owner_id=current_user.id,)
    db.add(team)
    db.flush()

    # creator auto-joins
    db.add(TeamMember(team_id=team.id, user_id=current_user.id,role="owner"))
    db.commit()
    db.refresh(team)
    return team

@router.post("/{team_id}/join", status_code=204)
def join_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    exists = (
        db.query(TeamMember)
        .filter_by(team_id=team_id, user_id=current_user.id)
        .first()
    )
    if exists:
        return

    db.add(TeamMember(team_id=team_id, user_id=current_user.id))
    db.commit()

@router.get("", response_model=list[TeamResponse])
def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # list workspaces current user belongs to
    rows = (
        db.query(Team)
        .join(TeamMember)
        .filter(TeamMember.user_id == current_user.id)
        .all()
    )
    return rows

@router.post("/{team_id}/add-workspace/{workspace_id}", status_code=204)
def add_workspace_to_team(
    team_id: int,
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # permission check AGAINST THE TARGET WORKSPACE
    member = (
        db.query(WorkspaceMember)
        .filter_by(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
        .first()
    )

    if not member or member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    db.add(TeamWorkspace(team_id=team.id, workspace_id=workspace_id))
    db.flush()

    # sync workspace members into team
    workspace_user_ids = {
        wm.user_id
        for wm in db.query(WorkspaceMember)
        .filter_by(workspace_id=workspace_id)
        .all()
    }

    existing_team_user_ids = {
        tm.user_id
        for tm in db.query(TeamMember)
        .filter_by(team_id=team.id)
        .all()
    }

    for user_id in workspace_user_ids - existing_team_user_ids:
        db.add(
            TeamMember(
                team_id=team.id,
                user_id=user_id,
                role="member",
            )
        )

    db.commit()


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
def list_members(
    team_id: int,
    db: Session = Depends(get_db),
    member: TeamMember = Depends(require_team_member),
):
    team = db.query(Team).filter_by(id=team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    members = (
        db.query(TeamMember)
        .filter_by(team_id=team_id)
        .all()
    )

    return [
        {
            "id": m.id,
            "team_id": m.team_id,
            "user_id": m.user_id,
            "role": m.role,
            "username": m.user.username,
            "email": m.user.email,
        }
        for m in members
    ]
