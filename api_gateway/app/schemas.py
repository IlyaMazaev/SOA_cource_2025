from pydantic import BaseModel, Field
from typing import Optional


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str


class LoginRequest(BaseModel):
    username: str
    password: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    birth_date: Optional[str] = None
    mail: Optional[str] = None
    phone: Optional[str] = None


class Post(BaseModel):
    id: str = None
    title: str
    description: str
    creator_id: str = None
    created_at: str = None
    updated_at: str = None
    is_private: bool = False
    tags: list[str] = Field(default_factory=list)


class CreatePostRequest(BaseModel):
    title: str
    description: str
    is_private: bool = False
    tags: list[str] = Field(default_factory=list)


class UpdatePostRequest(BaseModel):
    title: str = None
    description: str = None
    is_private: bool = None
    tags: list[str] = None

class CommentIn(BaseModel):
    content: str