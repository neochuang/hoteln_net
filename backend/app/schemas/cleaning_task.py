import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.cleaning_task import CleaningTaskStatus


class CleaningTaskBase(BaseModel):
    room_id: uuid.UUID
    assigned_to_user_id: uuid.UUID
    cleaning_type: str


class CleaningTaskCreate(CleaningTaskBase):
    pass


class CleaningTaskUpdateStatus(BaseModel):
    status: CleaningTaskStatus


class CleaningTaskResponse(CleaningTaskBase):
    id: uuid.UUID
    assigned_by_user_id: uuid.UUID
    status: CleaningTaskStatus
    created_at: datetime
    updated_at: datetime
    room_number: str | None = None
    cleaner_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
