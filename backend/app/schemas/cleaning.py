import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.cleaning import CleaningType, ReportedVia


class CleanCompleteRequest(BaseModel):
    cleaned_by_name: str | None = None
    notes: str | None = None


class CleaningRecordResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    cleaning_type: CleaningType
    started_at: datetime
    completed_at: datetime | None
    cleaned_by_name: str | None
    reported_via: ReportedVia | None
    api_key_id: uuid.UUID | None
    staff_user_id: uuid.UUID | None
    notes: str | None

    model_config = {"from_attributes": True}


class MarkCleaningResponse(BaseModel):
    room_id: uuid.UUID
    room_number: str
    status: str
    cleaning_record: CleaningRecordResponse

    model_config = {"from_attributes": True}


class CleanCompleteResponse(BaseModel):
    room_id: uuid.UUID
    room_number: str
    status: str
    cleaning_record: CleaningRecordResponse

    model_config = {"from_attributes": True}


class CleaningStatusRoom(BaseModel):
    room_id: uuid.UUID
    room_number: str
    floor: int
    room_type_name: str
    cleaning_type: CleaningType
    started_at: datetime
