import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.cleaning_request import CleaningRequestStatus


class CleaningRequestCreate(BaseModel):
    notes: str | None = Field(None, min_length=1, max_length=500)


class CleaningRequestResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    room_number: str
    api_key_id: uuid.UUID
    notes: str | None
    status: CleaningRequestStatus
    requested_at: datetime
    fulfilled_at: datetime | None
    fulfilled_by_cleaning_record_id: uuid.UUID | None
    cancelled_at: datetime | None
    cancelled_by_user_id: uuid.UUID | None

    model_config = {"from_attributes": True}
