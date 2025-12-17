from datetime import datetime
from pydantic import BaseModel, computed_field
from typing import List, Optional


class MediaResponse(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    mime_type: str | None
    description: Optional[str]
    created_at: datetime
    tags: Optional[str]  # 👈 THIS IS THE MISSING PIECE

    @computed_field
    @property
    def tags_list(self) -> List[str]:
        return self.tags.split(",") if self.tags else []

    class Config:
        from_attributes = True


class UpdateMediaRequest(BaseModel):
    original_filename: Optional[str]
    description: Optional[str]
    tags: Optional[List[str]]


class MediaListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[MediaResponse]


class MediaBase(BaseModel):
    id: int
    original_filename: str
    stored_filename: str
    size_bytes: int
    mime_type: str | None
    created_at: datetime
    file_type: str

    @staticmethod
    def compute_file_type(mime_type: str | None) -> str:
        if not mime_type:
            return "other"
        main = mime_type.split("/")[0]
        return main if main in {"image", "video", "audio"} else "other"

    @classmethod
    def from_orm(cls, obj):
        return cls(**obj.__dict__, file_type=cls.compute_file_type(obj.mime_type))

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


class RenameFileRequest(BaseModel):
    old_filename: str
    new_filename: str
