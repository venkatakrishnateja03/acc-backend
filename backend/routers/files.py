from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from models.media import Media
from core.config import fernet, FILES_DIR
import os, uuid

router = APIRouter(prefix="/files", tags=["files"])


def fake_current_user(db: Session):
    user = db.query(User).filter(User.id == 1).first()
    if not user:
        user = User(email="demo@example.com", username="demo", hashed_password="xx")
        db.add(user)
        db.commit()
    return user


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    user = fake_current_user(db)
    content = await file.read()

    encrypted = fernet.encrypt(content)

    stored_name = f"{uuid.uuid4().hex}.enc"
    path = os.path.join(FILES_DIR, stored_name)

    with open(path, "wb") as f:
        f.write(encrypted)

    media = Media(
        user_id=user.id,
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


@router.get("/")
def list_files(db: Session = Depends(get_db)):
    user = fake_current_user(db)
    return db.query(Media).filter(Media.user_id == user.id).all()
