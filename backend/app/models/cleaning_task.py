import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CleaningTaskStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class CleaningTask(Base):
    __tablename__ = "cleaning_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    assigned_to_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[CleaningTaskStatus] = mapped_column(
        Enum(CleaningTaskStatus), default=CleaningTaskStatus.pending, nullable=False
    )
    cleaning_type: Mapped[str] = mapped_column(nullable=False)  # daily or checkout
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    room = relationship("Room", back_populates="cleaning_tasks")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_tasks")
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id], back_populates="created_tasks")
