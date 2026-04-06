from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.backlog_entry import BacklogEntry, BacklogStatus
from app.models.game import Game, GamePlatform
from app.models.user import User
from app.schemas.backlog import (
    BacklogEntryCreate,
    BacklogEntryUpdate,
    BacklogEntryResponse,
)
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/backlog", tags=["backlog"])


@router.get("", response_model=list[BacklogEntryResponse])
async def get_my_backlog(
    status: BacklogStatus | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(BacklogEntry)
        .options(
            selectinload(BacklogEntry.game)
            .selectinload(Game.platforms)
            .selectinload(GamePlatform.platform)
        )
        .where(BacklogEntry.user_id == current_user.id)
    )
    if status:
        query = query.where(BacklogEntry.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{entry_id}", response_model=BacklogEntryResponse)
async def get_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry)
        .options(
            selectinload(BacklogEntry.game)
            .selectinload(Game.platforms)
            .selectinload(GamePlatform.platform)
        )
        .where(BacklogEntry.id == entry_id, BacklogEntry.user_id == current_user.id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Backlog entry not found")
    return entry


@router.post("", response_model=BacklogEntryResponse, status_code=201)
async def add_to_backlog(
    payload: BacklogEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Game).where(Game.id == payload.game_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Game not found")

    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.user_id == current_user.id,
            BacklogEntry.game_id == payload.game_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Game already in your backlog")

    entry = BacklogEntry(
        user_id=current_user.id,
        game_id=payload.game_id,
        status=payload.status,
        priority=payload.priority,
        hours_played=payload.hours_played,
    )
    db.add(entry)
    await db.commit()

    result = await db.execute(
        select(BacklogEntry)
        .options(
            selectinload(BacklogEntry.game)
            .selectinload(Game.platforms)
            .selectinload(GamePlatform.platform)
        )
        .where(BacklogEntry.id == entry.id)
    )
    return result.scalar_one()


@router.put("/{entry_id}", response_model=BacklogEntryResponse)
async def update_entry(
    entry_id: int,
    payload: BacklogEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Backlog entry not found")

    if payload.status is not None:
        entry.status = payload.status
    if payload.priority is not None:
        entry.priority = payload.priority
    if payload.hours_played is not None:
        entry.hours_played = payload.hours_played

    await db.commit()

    result = await db.execute(
        select(BacklogEntry)
        .options(
            selectinload(BacklogEntry.game)
            .selectinload(Game.platforms)
            .selectinload(GamePlatform.platform)
        )
        .where(BacklogEntry.id == entry_id)
    )
    return result.scalar_one()


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Backlog entry not found")
    await db.delete(entry)
    await db.commit()
