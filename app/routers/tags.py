from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.tag import Tag
from app.models.backlog_entry import BacklogEntry
from app.models.backlog_entry_tag import BacklogEntryTag
from app.models.user import User, UserRole
from app.schemas.tag import TagCreate, TagResponse
from app.dependencies import get_current_user

router = APIRouter(tags=["tags"])


@router.get("/api/tags", response_model=list[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tag))
    return result.scalars().all()


@router.post("/api/tags", response_model=TagResponse, status_code=201)
async def create_tag(
        payload: TagCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    tag = Tag(name=payload.name, created_by_id=current_user.id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


@router.delete("/api/tags/{tag_id}", status_code=204)
async def delete_tag(
        tag_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    is_owner = tag.created_by_id == current_user.id
    is_moderator = current_user.role in (UserRole.moderator, UserRole.admin)

    if not is_owner and not is_moderator:
        raise HTTPException(status_code=403, detail="Not allowed to delete this tag")

    await db.delete(tag)
    await db.commit()


@router.post("/api/backlog/{entry_id}/tags/{tag_id}", status_code=201)
async def attach_tag(
        entry_id: int,
        tag_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntry).where(
            BacklogEntry.id == entry_id,
            BacklogEntry.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Backlog entry not found")

    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Tag not found")

    result = await db.execute(
        select(BacklogEntryTag).where(
            BacklogEntryTag.entry_id == entry_id,
            BacklogEntryTag.tag_id == tag_id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Tag already attached")

    db.add(BacklogEntryTag(entry_id=entry_id, tag_id=tag_id))
    await db.commit()
    return {"detail": "Tag attached"}


@router.delete("/api/backlog/{entry_id}/tags/{tag_id}", status_code=204)
async def detach_tag(
        entry_id: int,
        tag_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(BacklogEntryTag).where(
            BacklogEntryTag.entry_id == entry_id,
            BacklogEntryTag.tag_id == tag_id,
        )
    )
    entry_tag = result.scalar_one_or_none()
    if not entry_tag:
        raise HTTPException(status_code=404, detail="Tag not attached to this entry")

    await db.delete(entry_tag)
    await db.commit()
