from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.media import Media
from core.config import fernet, FILES_DIR
import os, uuid
from routers.auth import get_current_user
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import asc, desc
from typing import Optional

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/")
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    # pagination
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    # filtering
    filename: Optional[str] = Query(None, description="Filter by original filename"),
    mime_type: Optional[str] = Query(None, description="Filter by mime type"),
    # sorting
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    base_query = db.query(Media).filter(Media.user_id == current_user.id)

    # filtering
    if filename:
        base_query = base_query.filter(Media.original_filename.ilike(f"%{filename}%"))

    if mime_type:
        base_query = base_query.filter(Media.mime_type == mime_type)

    # sorting
    order_by_clause = (
        asc(Media.created_at) if sort_order == "asc" else desc(Media.created_at)
    )
    base_query = base_query.order_by(order_by_clause)

    # total count before pagination
    total = base_query.count()

    # pagination
    files = base_query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": files,
    }


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    content = await file.read()

    encrypted = fernet.encrypt(content)

    stored_name = f"{uuid.uuid4().hex}.enc"
    path = os.path.join(FILES_DIR, stored_name)

    with open(path, "wb") as f:
        f.write(encrypted)

    media = Media(
        user_id=current_user.id,
        original_filename=file.filename,
        stored_filename=stored_name,
        stored_path=path,
        size_bytes=len(encrypted),
        mime_type=file.content_type,
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
    # 1. Find file owned by this user
    media = (
        db.query(Media)
        .filter(
            Media.user_id == current_user.id,
            Media.original_filename == filename,
        )
        .first()
    )

    if not media:
        raise HTTPException(status_code=404, detail="File not found")

    # 2. Ensure encrypted file exists
    if not os.path.exists(media.stored_path):
        raise HTTPException(status_code=404, detail="Stored file missing")

    # 3. Read encrypted content
    with open(media.stored_path, "rb") as f:
        encrypted_data = f.read()

    # 4. Decrypt
    try:
        decrypted_data = fernet.decrypt(encrypted_data)
    except Exception:
        raise HTTPException(status_code=500, detail="File decryption failed")

    # 5. Stream file back
    file_stream = BytesIO(decrypted_data)

    return StreamingResponse(
        file_stream,
        media_type=media.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{media.original_filename}"'
        },
    )
