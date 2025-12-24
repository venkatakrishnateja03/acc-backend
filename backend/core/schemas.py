from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, computed_field

class MediaResponse(BaseModel):
    id: int
    workspace_id: int
    original_filename: str
    size_bytes: int
    mime_type: str | None
    description: Optional[str]
    tags: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def tags_list(self) -> List[str]:
        return self.tags.split(",") if self.tags else []

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[MediaResponse]


class UpdateMediaRequest(BaseModel):
    original_filename: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class MediaBase(BaseModel):
    id: int
    workspace_id: int
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
        return cls(
            **obj.__dict__,
            file_type=cls.compute_file_type(obj.mime_type),
        )

    class Config:
        from_attributes = True

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
    new_filename: str


# Documents
class DocumentCreateRequest(BaseModel):
    title: str
    # Either `content` (text document) or `media_id` (file-backed document) must be provided.
    content: str | None = None
    media_id: int | None = None
    doc_type: str | None = "text"


class DocumentResponse(BaseModel):
    id: int
    workspace_id: int
    title: str
    media_id: int | None = None
    doc_type: str
    version: int
    created_at: datetime

    class Config:
        from_attributes = True


# Comments
class CommentCreateRequest(BaseModel):
    target_type: str
    target_id: int
    body: str


class CommentResponse(BaseModel):
    id: int
    workspace_id: int
    author_id: int | None
    target_type: str
    target_id: int
    body: str
    created_at: datetime

    class Config:
        from_attributes = True
