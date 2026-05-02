import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoomStatus(str, enum.Enum):
    available = "available"
    occupied = "occupied"
    cleaning = "cleaning"
    maintenance = "maintenance"


class RoomType(Base):
    __tablename__ = "room_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)
    base_price: Mapped[float] = mapped_column(Numeric(10, 2))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rooms = relationship("Room", back_populates="room_type")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_number: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer)
    room_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("room_types.id"))
    status: Mapped[RoomStatus] = mapped_column(Enum(RoomStatus), default=RoomStatus.available)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    room_type = relationship("RoomType", back_populates="rooms")
    cleaning_tasks = relationship("CleaningTask", back_populates="room")
