from datetime import datetime
from pydantic import BaseModel


class MediaBase(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    size_bytes: int
    mime_type: str | None
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 (for v1: orm_mode = True)


class UserBase(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
