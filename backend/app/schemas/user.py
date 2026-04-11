import uuid

from pydantic import BaseModel

from app.models.user import UserRole


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: UserRole = UserRole.staff


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}
