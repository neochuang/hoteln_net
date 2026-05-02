import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import require_role
from app.models.cleaning_task import CleaningTask, CleaningTaskStatus
from app.models.room import Room, RoomStatus
from app.models.user import User, UserRole
from app.models.cleaning import CleaningRecord, CleaningType, ReportedVia
from app.schemas.cleaning_task import (
    CleaningTaskCreate,
    CleaningTaskResponse,
    CleaningTaskUpdateStatus,
)

router = APIRouter()


@router.post("/tasks", response_model=CleaningTaskResponse)
async def create_task(
    body: CleaningTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    # Verify room exists
    room = (await db.execute(select(Room).where(Room.id == body.room_id))).scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify cleaner exists and has correct role
    cleaner = (await db.execute(select(User).where(User.id == body.assigned_to_user_id))).scalar_one_or_none()
    if not cleaner or cleaner.role != UserRole.cleaner:
        raise HTTPException(status_code=400, detail="Invalid cleaner ID")

    task = CleaningTask(
        room_id=body.room_id,
        assigned_to_user_id=body.assigned_to_user_id,
        assigned_by_user_id=current_user.id,
        cleaning_type=body.cleaning_type,
        status=CleaningTaskStatus.pending,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return CleaningTaskResponse(
        **task.__dict__,
        room_number=room.room_number,
        cleaner_name=cleaner.full_name
    )


@router.get("/tasks", response_model=list[CleaningTaskResponse])
async def list_tasks(
    status_filter: CleaningTaskStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(UserRole.admin, UserRole.staff)),
):
    query = (
        select(CleaningTask)
        .options(selectinload(CleaningTask.room), selectinload(CleaningTask.assigned_to))
        .order_by(CleaningTask.created_at.desc())
    )
    if status_filter:
        query = query.where(CleaningTask.status == status_filter)

    result = await db.execute(query)
    tasks = result.scalars().all()
    
    return [
        CleaningTaskResponse(
            **t.__dict__,
            room_number=t.room.room_number,
            cleaner_name=t.assigned_to.full_name
        ) for t in tasks
    ]


@router.get("/my-tasks", response_model=list[CleaningTaskResponse])
async def list_my_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.cleaner)),
):
    # Get pending, in_progress, and tasks completed today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = (
        select(CleaningTask)
        .options(selectinload(CleaningTask.room))
        .where(CleaningTask.assigned_to_user_id == current_user.id)
        .where(
            (CleaningTask.status.in_([CleaningTaskStatus.pending, CleaningTaskStatus.in_progress])) |
            ((CleaningTask.status == CleaningTaskStatus.completed) & (CleaningTask.updated_at >= today_start))
        )
        .order_by(CleaningTask.status.desc(), CleaningTask.created_at.desc())
    )

    result = await db.execute(query)
    tasks = result.scalars().all()

    return [
        CleaningTaskResponse(
            **t.__dict__,
            room_number=t.room.room_number,
            cleaner_name=current_user.full_name
        ) for t in tasks
    ]


@router.put("/tasks/{task_id}/status", response_model=CleaningTaskResponse)
async def update_task_status(
    task_id: uuid.UUID,
    body: CleaningTaskUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.cleaner, UserRole.admin, UserRole.staff)),
):
    query = (
        select(CleaningTask)
        .options(selectinload(CleaningTask.room), selectinload(CleaningTask.assigned_to))
        .where(CleaningTask.id == task_id)
    )
    result = await db.execute(query)
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If cleaner, they can only update their own tasks
    if current_user.role == UserRole.cleaner and task.assigned_to_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")

    old_status = task.status
    task.status = body.status

    # Business logic for room status and records
    if body.status == CleaningTaskStatus.in_progress:
        task.room.status = RoomStatus.cleaning
    elif body.status == CleaningTaskStatus.completed:
        # Create a CleaningRecord
        record = CleaningRecord(
            room_id=task.room_id,
            cleaning_type=CleaningType.daily if task.cleaning_type == "daily" else CleaningType.checkout,
            started_at=task.created_at, # Rough estimate or use task's actual in_progress start if tracked
            completed_at=datetime.now(timezone.utc),
            cleaned_by_name=task.assigned_to.full_name,
            reported_via=ReportedVia.staff,
            staff_user_id=task.assigned_to_user_id,
        )
        db.add(record)
        
        # Room status logic (simplified: default back to available or occupied if guest is there)
        # Note: In a full implementation, check for active reservation
        task.room.status = RoomStatus.available # Default

    await db.commit()
    await db.refresh(task)

    return CleaningTaskResponse(
        **task.__dict__,
        room_number=task.room.room_number,
        cleaner_name=task.assigned_to.full_name
    )
