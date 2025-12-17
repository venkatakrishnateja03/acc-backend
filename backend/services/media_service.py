import os
from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.media import Media
from sqlalchemy.exc import IntegrityError


def get_user_file(db: Session, user_id: int, filename: str) -> Media:
    media = (
        db.query(Media)
        .filter(
            Media.user_id == user_id,
            Media.original_filename == filename,
        )
        .first()
    )

    if not media:
        raise HTTPException(status_code=404, detail="File not found")

    return media


def get_user_file_id(db: Session, user_id: int, media_id: int) -> Media:
    media = (
        db.query(Media)
        .filter(
            Media.user_id == user_id,
            Media.id == media_id,
        )
        .first()
    )

    if not media:
        raise HTTPException(status_code=404, detail="File not found")

    return media


def rename_file(db: Session, media: Media, new_filename: str) -> Media:
    media.original_filename = new_filename
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A file with this name already exists",
        )
    db.refresh(media)
    return media


def delete_file(db: Session, media: Media) -> None:
    path: str = media.stored_path

    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete file from storage",
            )

    db.delete(media)
    db.commit()


def update_media(
    db: Session,
    media: Media,
    *,
    original_filename: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> Media:
    if original_filename is not None:
        media.original_filename = original_filename

    if description is not None:
        media.description = description

    if tags is not None:
        media.tags = ",".join(tags)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A file with this name already exists",
        )

    db.refresh(media)
    return media
