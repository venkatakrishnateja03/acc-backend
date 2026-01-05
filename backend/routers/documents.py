from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.document import Document
from dependencies.permissions import require_workspace_member, require_workspace_role
from core.schemas import DocumentCreateRequest, DocumentResponse
from models.media import Media

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse)
def create_document(
    workspace_id: int,
    payload: DocumentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN", "EDITOR"])),
):
    # Validate payload: must provide either content (text) or media_id (file-backed)
    if not (payload.content or payload.media_id):
        raise HTTPException(status_code=422, detail="Either content or media_id must be provided")

    # If media_id provided, ensure the media exists and belongs to this workspace
    if payload.media_id is not None:
        media = db.query(Media).filter_by(id=payload.media_id).first()
        if not media or media.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail="Invalid media_id for this workspace")

    doc = Document(
        workspace_id=workspace_id,
        title=payload.title,
        content=payload.content or "",
        doc_type=("file" if payload.media_id else (payload.doc_type or "text")),
        media_id=payload.media_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    rows = db.query(Document).filter_by(workspace_id=workspace_id).all()
    return rows


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(
    workspace_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    doc = db.query(Document).filter_by(workspace_id=workspace_id, id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.put("/{doc_id}", response_model=DocumentResponse)
def update_document(
    workspace_id: int,
    doc_id: int,
    payload: DocumentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN", "EDITOR"])),
):
    doc = db.query(Document).filter_by(workspace_id=workspace_id, id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    # Allow switching between text and file-backed documents; require at least one.
    if not (payload.content or payload.media_id):
        raise HTTPException(status_code=422, detail="Either content or media_id must be provided")
    if payload.media_id is not None:
        media = db.query(Media).filter_by(id=payload.media_id).first()
        if not media or media.workspace_id != workspace_id:
            raise HTTPException(status_code=400, detail="Invalid media_id for this workspace")

    doc.title = payload.title
    doc.content = payload.content or doc.content or ""
    doc.media_id = payload.media_id
    doc.doc_type = ("file" if payload.media_id else (payload.doc_type or doc.doc_type))
    doc.version = doc.version + 1
    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{doc_id}")
def delete_document(
    workspace_id: int,
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN"])),
):
    doc = db.query(Document).filter_by(workspace_id=workspace_id, id=doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    try:
        from services.audit_service import log_event

        log_event(db, workspace_id=workspace_id, actor_id=current_user.id, action="document.delete", detail=doc.title)
    except Exception:
        pass
    return {"detail": "Document deleted"}
