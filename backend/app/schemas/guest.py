import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.guest import IDType


class GuestCreate(BaseModel):
    first_name: str
    last_name: str
    id_type: IDType
    id_number: str
    phone: str
    email: str | None = None
    nationality: str
    notes: str | None = None


class GuestUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    id_type: IDType | None = None
    id_number: str | None = None
    phone: str | None = None
    email: str | None = None
    nationality: str | None = None
    notes: str | None = None


class GuestResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    id_type: IDType
    id_number: str
    phone: str
    email: str | None
    nationality: str
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
