from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Query,
    Form,
)
from sqlalchemy.orm import Session
from typing import Optional
from io import BytesIO
import os
import uuid

from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc

from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.media import Media
from dependencies.permissions import require_workspace_member, require_workspace_role

from core.config import fernet, FILES_DIR
from core.schemas import (
    MediaListResponse,
    MediaResponse,
    UpdateMediaRequest,
)

router = APIRouter(
    prefix="/workspaces/{workspace_id}/media",
    tags=["media"],
)
def get_media_or_404(
    db: Session,
    workspace_id: int,
    media_id: int,
) -> Media:
    media = (
        db.query(Media)
        .filter_by(id=media_id, workspace_id=workspace_id)
        .first()
    )
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


# ======================================================
# Routes
# ======================================================

@router.get("/", response_model=MediaListResponse)
def list_media(
    workspace_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member: User = Depends(require_workspace_member),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    filename: Optional[str] = Query(None),
    # `type` is optional; when provided we perform a simple mime-type prefix filter.
    type: Optional[str] = Query(None),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    # membership validated by dependency

    query = db.query(Media).filter(Media.workspace_id == workspace_id)

    if filename:
        query = query.filter(Media.original_filename.ilike(f"%{filename}%"))

    if type:
        t = type.strip().lower()
        # Allowed simple prefixes to filter by. If `type` doesn't match one of these,
        # we do no filtering (minimal validation, non-strict).
        allowed_prefixes = {"image", "video", "audio", "application", "text"}
        if t in allowed_prefixes:
            query = query.filter(Media.mime_type.like(f"{t}/%"))

    order = asc(Media.created_at) if sort_order == "asc" else desc(Media.created_at)
    query = query.order_by(order)

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": items,
    }


@router.post("/upload", response_model=MediaResponse)
async def upload_media(
    workspace_id: int,
    file: UploadFile = File(...),
    description: str | None = Form(None),
    tags: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN", "EDITOR"])),
):
    # membership & role validated by dependency

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    encrypted = fernet.encrypt(content)

    stored_filename = f"{uuid.uuid4().hex}.enc"
    stored_path = os.path.join(FILES_DIR, stored_filename)

    with open(stored_path, "wb") as f:
        f.write(encrypted)

    media = Media(
        workspace_id=workspace_id,
        uploaded_by=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        stored_path=stored_path,
        size_bytes=len(encrypted),
        mime_type=file.content_type,
        description=description,
        tags=tags.strip() if tags else None,
    )

    db.add(media)
    db.commit()
    db.refresh(media)
    try:
        from services.audit_service import log_event

        log_event(db, workspace_id=workspace_id, actor_id=current_user.id, action="media.upload", detail=media.original_filename)
    except Exception:
        pass
    return media


@router.get("/{media_id}/download")
def download_media(
    workspace_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_member),
):
    media = get_media_or_404(db, workspace_id, media_id)

    if not os.path.exists(media.stored_path):
        raise HTTPException(status_code=404, detail="Stored file missing")

    with open(media.stored_path, "rb") as f:
        decrypted = fernet.decrypt(f.read())

    return StreamingResponse(
        BytesIO(decrypted),
        media_type=media.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{media.original_filename}"'
        },
    )


@router.put("/{media_id}", response_model=MediaResponse)
def update_media(
    workspace_id: int,
    media_id: int,
    payload: UpdateMediaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN", "EDITOR"])),
):
    media = get_media_or_404(db, workspace_id, media_id)

    if payload.original_filename is not None:
        media.original_filename = payload.original_filename
    if payload.description is not None:
        media.description = payload.description
    if payload.tags is not None:
        media.tags = ",".join(payload.tags)

    db.commit()
    db.refresh(media)
    return media


@router.delete("/{media_id}")
def delete_media(
    workspace_id: int,
    media_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _member = Depends(require_workspace_role(["OWNER", "ADMIN"])),
):
    media = get_media_or_404(db, workspace_id, media_id)

    if os.path.exists(media.stored_path):
        os.remove(media.stored_path)

    db.delete(media)
    db.commit()
    try:
        from services.audit_service import log_event

        log_event(db, workspace_id=workspace_id, actor_id=current_user.id, action="media.delete", detail=media.original_filename)
    except Exception:
        pass
    return {"detail": "Media deleted"}
