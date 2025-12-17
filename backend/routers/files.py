from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Form
from sqlalchemy.orm import Session
from typing import Optional
from io import BytesIO
import os, uuid
from core.schemas import MediaListResponse
from db.database import get_db
from routers.auth import get_current_user
from models.user import User
from models.media import Media
from core.config import fernet, FILES_DIR
from core.schemas import RenameFileRequest, MediaResponse
from core.schemas import UpdateMediaRequest
from services.media_service import (
    get_user_file,
    rename_file as rename_media,
    delete_file as delete_media,
    update_media,
    get_user_file_id,
)

from fastapi.responses import StreamingResponse
from sqlalchemy import asc, desc

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/", response_model=MediaListResponse)
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    filename: Optional[str] = Query(None, description="Filter by original filename"),
    type: Optional[str] = Query(
        None,
        description="File category: image | video | audio | other",
        regex="^(image|video|audio|other)$",
    ),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    query = db.query(Media).filter(Media.user_id == current_user.id)

    if filename:
        query = query.filter(Media.original_filename.ilike(f"%{filename}%"))
    if type:
        if type in {"image", "video", "audio"}:
            query = query.filter(Media.mime_type.like(f"{type}/%"))
        else:  # other
            query = query.filter(
                ~Media.mime_type.like("image/%"),
                ~Media.mime_type.like("video/%"),
                ~Media.mime_type.like("audio/%"),
            )

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
async def upload_file(
    file: UploadFile = File(...),
    description: str | None = Form(None),
    tags: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    encrypted = fernet.encrypt(content)

    stored_filename = f"{uuid.uuid4().hex}.enc"
    stored_path = os.path.join(FILES_DIR, stored_filename)

    with open(stored_path, "wb") as f:
        f.write(encrypted)
    tags_str = tags.strip() if tags else None

    media = Media(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_filename,
        stored_path=stored_path,
        size_bytes=len(encrypted),
        mime_type=file.content_type,
        description=description,
        tags=tags_str,
    )

    db.add(media)
    db.commit()
    db.refresh(media)
    return media


@router.get("/download/{filename}")
def download_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media = get_user_file(db, current_user.id, filename)

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


@router.patch("/rename", response_model=MediaResponse)
def rename_file(
    payload: RenameFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media = get_user_file(db, current_user.id, payload.old_filename)
    return rename_media(db, media, payload.new_filename)


@router.delete("/{filename}")
def delete_file(
    filename: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media = get_user_file(db, current_user.id, filename)
    delete_media(db, media)
    return {"detail": "File deleted successfully"}


@router.put("/{media_id}", response_model=MediaResponse)
def update_media_endpoint(
    media_id: int,
    payload: UpdateMediaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    media = get_user_file_id(db, current_user.id, int(media_id))

    return update_media(
        db,
        media,
        original_filename=payload.original_filename,
        description=payload.description,
        tags=payload.tags,
    )
