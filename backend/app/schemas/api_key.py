import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    room_id: uuid.UUID | None = None


class ApiKeyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    room_id: uuid.UUID | None = None


class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    key_prefix: str
    name: str
    is_active: bool
    room_id: uuid.UUID | None = None
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str
