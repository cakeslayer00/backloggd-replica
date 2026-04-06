from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.platform import Platform
from app.models.user import UserRole
from app.schemas.platform import PlatformCreate, PlatformResponse
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformResponse])
async def list_platforms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Platform))
    return result.scalars().all()


@router.get("/{platform_id}", response_model=PlatformResponse)
async def get_platform(platform_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Platform).where(Platform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    return platform


@router.post("", response_model=PlatformResponse, status_code=201)
async def create_platform(
    payload: PlatformCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Platform).where(Platform.name == payload.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Platform with this slug already exists")

    platform = Platform(name=payload.name)
    db.add(platform)
    await db.commit()
    await db.refresh(platform)
    return platform


@router.delete("/{platform_id}", status_code=204)
async def delete_platform(
    platform_id: int,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role(UserRole.admin)),
):
    result = await db.execute(select(Platform).where(Platform.id == platform_id))
    platform = result.scalar_one_or_none()
    if not platform:
        raise HTTPException(status_code=404, detail="Platform not found")
    await db.delete(platform)
    await db.commit()